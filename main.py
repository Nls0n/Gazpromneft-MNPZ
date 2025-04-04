import json
import time
import psycopg2
from psycopg2.extras import RealDictCursor
from PyQt6.QtWidgets import (
    QApplication, QMainWindow,
    QPushButton, QVBoxLayout,
    QHBoxLayout, QWidget, QLabel,
    QSpacerItem, QSizePolicy,
    QMessageBox
)
from PyQt6.QtGui import QFont, QPixmap
from PyQt6.QtCore import Qt, QTimer


class Compressor:
    def __init__(self, pwr):
        self.current_power = pwr
        self.powers = [0, 30, 50, 75, 90, 100]
        if self.current_power == 100:
            self.role = 'main'
            self.condition = 'on'
        else:
            self.role = 'backup'
            self.condition = 'off'

    def toggle_on(self):
        self.condition = 'on'

    def toggle_off(self):
        self.condition = 'off'


conn = psycopg2.connect(
    dbname='case_logs',
    user='postgres',
    password='A12138877',
    host='localhost',
    port='5432',
    cursor_factory=RealDictCursor)
cursor = conn.cursor()
cursor.execute(
    '''SELECT compressor1_state, compressor2_state 
       FROM compressors_logs 
       ORDER BY operation_id
       DESC LIMIT 1''')
data = dict(cursor.fetchone())

compressor1 = Compressor(
    data['compressor1_state']['power'])
compressor2 = Compressor(
    data['compressor2_state']['power'])

ratios = [
    (100, 0),
    (90, 0),
    (75, 30),
    (50, 50),
    (30, 75),
    (0, 90),
    (0, 100)
]

images = {
    0: 'images/compressor_0.png',
    30: 'images/compressor_30.png',
    50: 'images/compressor_50.png',
    75: 'images/compressor_75.png',
    90: 'images/compressor_90.png',
    100: 'images/compressor_100.png',
}


def logging_func(func: callable, comp1: Compressor, comp2: Compressor):
    cursor.execute(
        '''
        INSERT INTO compressors_logs
        (function_name, compressor1_state, compressor2_state)
        VALUES (%s, %s, %s)
        ''',
        (func.__name__,
         json.dumps({
             "power": comp1.current_power,
             "role": comp1.role,
             "condition": comp1.condition
         }),
         json.dumps({
             "power": comp2.current_power,
             "role": comp2.role,
             "condition": comp2.condition
         }),
         ))
    conn.commit()


def switch() -> None:
    global compressor1, compressor2
    increment = 0
    time.sleep(120)

    def step():
        nonlocal increment
        if compressor1.condition == 'on' and compressor2.condition == 'on':
            if compressor1.role == 'main':
                for increment in range(len(ratios)):
                    compressor1.current_power = ratios[increment][0]
                    compressor2.current_power = ratios[increment][1]
                    if (compressor1.current_power == 90 or
                            compressor2.current_power == 90):
                        time.sleep(1)
                    else:
                        time.sleep(10)
                    increment += 1
                    window.update_compressors_display()
                    if compressor2.current_power == 100:
                        compressor1.role, compressor2.role = 'backup', 'main'
                        window.update_display()
                    QTimer.singleShot(1000, step)
        else:
            for increment in range(len(ratios)):
                compressor2.current_power = ratios[increment][0]
                compressor1.current_power = ratios[increment][1]
                if compressor1.current_power == 90 or compressor2.current_power == 90:
                    time.sleep(2)
                else:
                    time.sleep(2)
                increment += 1
                window.update_compressors_display()
                if compressor1.current_power == 100:
                    compressor2.role, compressor1.role = 'backup', 'main'
                QTimer.singleShot(1000, step)

    step()
    logging_func(switch, compressor1, compressor2)


def start_backup():
    if compressor1.role == 'backup':
        compressor1.toggle_on()
    elif compressor2.role == 'backup':
        compressor2.toggle_on()


def stop_backup():
    if compressor1.role == 'backup':
        compressor1.toggle_off()
    elif compressor2.role == 'backup':
        compressor2.toggle_off()


names = {
    'main': 'Основной компрессор',
    'backup': 'Резервный компрессор'
}

status = {
    'on': 'Включен',
    'off': 'Выключен'
}


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Управление компрессорами")
        self.showFullScreen()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        self.label = QLabel("Управление компрессорами")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        main_layout.addWidget(self.label)

        main_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        image_layout = QHBoxLayout()
        images_container = QWidget()
        images_layout = QHBoxLayout()
        images_container.setLayout(images_layout)

        images_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        image1_container = QVBoxLayout()
        self.image1 = QLabel()
        filename1 = images[compressor1.current_power]
        self.pixmap1 = QPixmap(filename1)
        self.update_image(self.image1, self.pixmap1)
        self.image1_label = QLabel(
            f'{names[compressor1.role]}\nПроизводительность: {compressor1.current_power}%\nСтатус: {status[compressor1.condition]}')
        self.image1_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image1_label.setFont(QFont("Arial", 30))
        image1_container.addWidget(self.image1)
        image1_container.addWidget(self.image1_label)

        image2_container = QVBoxLayout()
        self.image2 = QLabel()
        filename2 = images[compressor2.current_power]
        self.pixmap2 = QPixmap(filename2)
        self.update_image(self.image2, self.pixmap2)
        self.image2_label = QLabel(
            f'{names[compressor2.role]}\nПроизводительность: {compressor2.current_power}%\nСтатус: {status[compressor2.condition]}')
        self.image2_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image2_label.setFont(QFont("Arial", 30))
        image2_container.addWidget(self.image2)
        image2_container.addWidget(self.image2_label)

        images_layout.addLayout(image1_container)
        images_layout.addSpacing(400)
        images_layout.addLayout(image2_container)

        images_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        main_layout.addWidget(images_container)

        main_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        image_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        image_layout.addWidget(self.image1)
        image_layout.addSpacing(300)
        image_layout.addWidget(self.image2)
        image_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        main_layout.addLayout(image_layout)

        main_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        button_layout = QHBoxLayout()

        self.start_button = self._create_large_button("Пуск компрессора", "#4CAF50", self.start_compressor)
        self.switch_button = self._create_large_button("Переход компрессорами", "#FFC107", self.switch_compressors)
        self.stop_backup_button = self._create_large_button("Остановка резервного компрессора", "#F44336",
                                                            self.stop_backup_compressor)

        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.switch_button)
        button_layout.addWidget(self.stop_backup_button)

        self.animation_timer = QTimer()

        main_layout.addLayout(button_layout)

        self.current_step = 0
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.update_compressors_state)
        self.animation_direction = 1  # 1 - вперед по списку ratios, -1 - назад
        self.current_ratio_index = 0
        if compressor1.current_power == 100:
            self.first = compressor1
        else:
            self.first = compressor2
        self.image_cache = {
            power: QPixmap(path).scaled(
                self.width() // 3,
                self.width() // 3,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            for power, path in images.items()
        }

    def update_image(self, label, pixmap):
        size = self.width() // 3  # 33% ширины окна
        scaled_pixmap = pixmap.scaled(
            size, size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        label.setPixmap(scaled_pixmap)

    def _create_large_button(self, text, color, handler):
        button = QPushButton(text)
        button.setFont(QFont("Arial", 18))
        button.setMinimumHeight(60)
        button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        button.setStyleSheet(f"""
            background-color: {color};
            color: {'white' if color in ["#4CAF50", "#F44336"] else 'black'};
            border-radius: 8px;
            padding: 15px;
        """)
        button.clicked.connect(handler)
        return button

    def start_compressor(self):
        self.label.setText("Запущен резервный компрессор")
        start_backup()
        self.update_compressors_display()
        logging_func(self.start_compressor, compressor1, compressor2)

    def stop_backup_compressor(self):
        self.label.setText("Резервный компрессор остановлен")
        stop_backup()
        self.update_compressors_display()
        logging_func(stop_backup, compressor1, compressor2)

    def update_compressors_display(self):
        """Обновляет отображение компрессоров"""
        try:
            # Обновляем изображения
            self.image1.setPixmap(
                QPixmap(images[compressor1.current_power]).scaled(
                    self.width() // 3,
                    self.width() // 3,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
            )
            self.image2.setPixmap(
                QPixmap(images[compressor2.current_power]).scaled(
                    self.width() // 3,
                    self.width() // 3,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
            )
            # Обновляем подписи
            self.image1_label.setText(
                f'{names[compressor1.role]}\n Производительность: {compressor1.current_power}%\n Статус: {status[compressor1.condition]}')
            self.image2_label.setText(
                f'{names[compressor2.role]}\n Производительность: {compressor2.current_power}%\n Статус: {status[compressor2.condition]}')

        except Exception as e:
            pass

    def update_compressors_state(self):
        """Обновление состояния компрессоров и их отображения"""
        if 0 <= self.current_ratio_index < len(ratios):
            if self.first == compressor2:
                power2, power1 = ratios[self.current_ratio_index]
                compressor1.condition = 'on'
            else:
                power1, power2 = ratios[self.current_ratio_index]
                compressor2.condition = 'on'
            compressor1.current_power = power1
            compressor2.current_power = power2

            compressor1.role = 'main' if power1 == 100 else 'backup' if power1 == 0 else compressor1.role
            compressor2.role = 'main' if power2 == 100 else 'backup' if power2 == 0 else compressor2.role

            self.update_display()

            self.current_ratio_index += self.animation_direction

            if self.current_ratio_index >= len(ratios):
                self.animation_timer.stop()
                if compressor1.current_power == 100:
                    compressor1.role = 'main'
                    self.first = compressor1
                    self.image1_label.setText(
                        f'{names[compressor1.role]}\nПроизводительность: {compressor1.current_power}%\nСтатус: {status[compressor1.condition]}')
                if compressor2.current_power == 100:
                    compressor2.role = 'main'
                    self.first = compressor2
                    self.image2_label.setText(
                        f'{names[compressor2.role]}\nПроизводительность: {compressor2.current_power}%\nСтатус: {status[compressor2.condition]}')
                self.label.setText("Переключение завершено")
                logging_func(switch, compressor1, compressor2)
        else:
            self.animation_timer.stop()

    def update_display(self):
        # Обновляем изображения
        self.image1.setPixmap(self.image_cache[compressor1.current_power])
        self.image2.setPixmap(self.image_cache[compressor2.current_power])

        # Обновляем подписи с указанием роли
        self.image1_label.setText(
            f"{names[compressor1.role]}\n"
            f"Производительность: {compressor1.current_power}%\n"
            f"Статус: {status[compressor1.condition]}"
        )
        self.image2_label.setText(
            f"{names[compressor2.role]}\n"
            f"Производительность: {compressor2.current_power}%\n"
            f"Статус: {status[compressor2.condition]}"
        )

    def switch_compressors(self):
        """Запуск анимации переключения компрессоров"""
        if compressor2.condition != 'on' or compressor1.condition != 'on':
            QMessageBox.critical(
                self,
                'Ошибка',
                'Не все компрессора включены',
                buttons=QMessageBox.StandardButton.Ok,
                defaultButton=QMessageBox.StandardButton.Ok
            )
        elif not self.animation_timer.isActive():
            self.label.setText("Идет переключение компрессоров...")
            self.current_ratio_index = 0
            self.animation_direction = 1
            self.animation_timer.start(2000)


app = QApplication([])
window = MainWindow()
window.show()
app.exec()
