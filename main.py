"""
Игра «Крипто Кликер» на PyQt6
"""
import sys
import os
import json
import random
import time
from PyQt6.QtWidgets import *
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QPoint
from PyQt6.QtGui import QFont, QColor, QLinearGradient, QPainter
from PyQt6.QtSvgWidgets import QSvgWidget

# Получаем абсолютный путь к папке с файлом main.py
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class CryptoClickerLogic:
    """Класс логики игры, содержит все данные и расчеты"""

    def __init__(self):
        # Данные уровней
        self.levels = [
            {"name": "Dodgecoin", "min": 0, "max": 5000, "icon": "Ð", "svg": "dogecoin.svg", "theme": 1},
            {"name": "Litecoin", "min": 5000, "max": 14000, "icon": "Ł", "svg": "litecoin.svg", "theme": 1},
            {"name": "Solana", "min": 14000, "max": 26000, "icon": "◎", "svg": "solana.svg", "theme": 1},
            {"name": "Binance Coin", "min": 26000, "max": 42000, "icon": "BNB", "svg": "BNB.svg", "theme": 2},
            {"name": "Ripple", "min": 42000, "max": 62000, "icon": "XRP", "svg": "Ripple.svg", "theme": 2},
            {"name": "Tether", "min": 62000, "max": 86000, "icon": "₮", "svg": "Tether.svg", "theme": 2},
            {"name": "Etherium", "min": 86000, "max": 114000, "icon": "Ξ", "svg": "ethereum.svg", "theme": 3},
            {"name": "Bitcoin", "min": 114000, "max": float('inf'), "icon": "₿", "svg": "bitcoin.svg", "theme": 3}
        ]

        # Игровые показатели
        self.balance = 0.0
        self.total_clicks = 0
        self.click_power = 1.0
        self.passive_income = 0.0
        self.click_per_level = 1.0
        
        # Временные бонусы
        self.bonus_click_multiplier = 1.0
        self.bonus_click_expire = 0
        self.bonus_level_multiplier = 1.0
        self.bonus_level_expire = 0
        self.bonus_passive_multiplier = 1.0
        self.bonus_passive_expire = 0
        
        # Механика принудительной смены кнопки клика
        self.current_click_button = "left"  # left, right, space
        self.button_challenge_active = False
        self.button_challenge_required = "left"
        self.button_challenge_time_left = 0
        self.button_last_success = 0

        # Улучшения: [название, базовая стоимость, множитель эффекта, текущий уровень]
        self.passive_upgrades = [
            ["Виртуальный майнер", 10, 1.0, 0],
            ["Видеокарта RX 7900", 25, 5.0, 0],
            ["Майнинг ферма", 100, 25.0, 0],
            ["Облачный майнинг", 250, 100.0, 0],
            ["ASIC устройство", 1000, 500.0, 0],
            ["Квантовый компьютер", 5000, 2500.0, 0]
        ]

        self.click_upgrades = [
            ["Усиленный клик", 15, 0.5, 0],
            ["Двойной клик", 50, 1.5, 0],
            ["Супер клик", 150, 4.0, 0],
            ["Мега клик", 500, 10.0, 0],
            ["Гига клик", 2000, 30.0, 0],
            ["Ультимативный клик", 10000, 100.0, 0]
        ]

        self.level_upgrades = [
            ["Быстрый прогресс I", 20, 1, 0],
            ["Быстрый прогресс II", 75, 2, 0],
            ["Ускорение уровня", 200, 4, 0],
            ["Прокачка опыта", 600, 8, 0],
            ["Мастер уровней", 2500, 15, 0],
            ["Легенда прокачки", 10000, 30, 0]
        ]

    def get_current_level(self):
        """Определяет текущий уровень по общему количеству кликов"""
        for i, level in reversed(list(enumerate(self.levels))):
            if self.total_clicks >= level["min"]:
                return i, level
        return 0, self.levels[0]

    def get_level_progress(self):
        """Возвращает прогресс в процентах ДО СЛЕДУЮЩЕГО УРОВНЯ (при переходе сбрасывается)"""
        level_idx, level = self.get_current_level()

        if level_idx == len(self.levels) - 1:
            return 100.0

        previous = self.levels[level_idx]["min"]
        next_level = self.levels[level_idx]["max"]

        progress = (self.total_clicks - previous) / (next_level - previous)
        return min(progress * 100, 100.0)

    def process_click(self):
        """Обрабатывает клик по основной кнопке"""
        self.balance += self.click_power * self.bonus_click_multiplier
        self.total_clicks += int(self.click_per_level * self.bonus_level_multiplier)

    def process_passive_income(self):
        """Добавляет пассивный доход к балансу"""
        self.balance += self.passive_income * self.bonus_passive_multiplier
        
        # Обновляем таймеры бонусов
        self.bonus_click_expire -= 1
        self.bonus_level_expire -= 1
        self.bonus_passive_expire -= 1
        
        if self.bonus_click_expire <= 0:
            self.bonus_click_multiplier = 1.0
        if self.bonus_level_expire <= 0:
            self.bonus_level_multiplier = 1.0
        if self.bonus_passive_expire <= 0:
            self.bonus_passive_multiplier = 1.0
            
        # Обработка таймера задания смены кнопки
        if self.button_challenge_active:
            self.button_challenge_time_left -= 1
            if time.time() - self.button_last_success > 5:
                # Сброс всего прогресса
                self.total_clicks = 0
                self.balance = 0
                self.button_challenge_active = False
                self.current_click_button = "left"

    def get_upgrade_cost(self, upgrade):
        """Рассчитывает стоимость улучшения"""
        base_cost, level = upgrade[1], upgrade[3]
        return base_cost * (2 ** level)

    def buy_upgrade(self, upgrade_type, index):
        """Покупка улучшения"""
        if upgrade_type == "passive":
            upgrade = self.passive_upgrades[index]
        elif upgrade_type == "click":
            upgrade = self.click_upgrades[index]
        elif upgrade_type == "level":
            upgrade = self.level_upgrades[index]
        else:
            return False

        cost = self.get_upgrade_cost(upgrade)

        if self.balance >= cost:
            self.balance -= cost
            upgrade[3] += 1

            # Применяем эффект улучшения
            if upgrade_type == "passive":
                self.passive_income += upgrade[2]
            elif upgrade_type == "click":
                self.click_power += upgrade[2]
            elif upgrade_type == "level":
                self.click_per_level += upgrade[2]

            return True
        return False

class ShopWindow(QWidget):
    """Окно магазина улучшений"""

    def __init__(self, logic, update_callback):
        super().__init__()
        self.logic = logic
        self.update_callback = update_callback
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Магазин улучшений")
        self.setMinimumSize(700, 500)

        layout = QVBoxLayout()

        # Вкладки
        self.tabs = QTabWidget()

        # Вкладка Пассивный доход
        self.passive_tab = QWidget()
        self.passive_layout = QVBoxLayout(self.passive_tab)
        self.tabs.addTab(self.passive_tab, "Пассивный доход")

        # Вкладка Сила клика
        self.click_tab = QWidget()
        self.click_layout = QVBoxLayout(self.click_tab)
        self.tabs.addTab(self.click_tab, "Сила клика")

        # Вкладка Прокачка уровня
        self.level_tab = QWidget()
        self.level_layout = QVBoxLayout(self.level_tab)
        self.tabs.addTab(self.level_tab, "Прокачка уровня")

        layout.addWidget(self.tabs)
        self.setLayout(layout)

        self.update_shop()

    def update_theme(self, theme_level):
        """Обновляет стилизацию окна магазина согласно теме уровня"""
        if theme_level == 1:
            self.setStyleSheet("""
                QWidget {
                    background-color: #1F2833;
                    color: #C5C6C7;
                }
                QTabWidget::pane {
                    border: 1px solid #45A29E;
                    background-color: rgba(30, 30, 40, 0.9);
                }
                QTabBar::tab {
                    background-color: #0B0C10;
                    color: #C5C6C7;
                    padding: 8px 20px;
                    border: 1px solid #45A29E;
                }
                QTabBar::tab:selected {
                    background-color: #1F2833;
                    color: #66FCF1;
                }
            """)
        elif theme_level in (2,3):
            self.setStyleSheet("""
                QWidget {
                    background-color: #2D1B4E;
                    color: #FFB347;
                }
                QTabWidget::pane {
                    border: 1px solid #E94560;
                    background-color: #16213E;
                }
                QTabBar::tab {
                    background-color: #1E0A2E;
                    color: #FFB347;
                    padding: 8px 20px;
                    border: 1px solid #E94560;
                }
                QTabBar::tab:selected {
                    background-color: #2D1B4E;
                    color: #FFD700;
                }
            """)
        else:
            self.setStyleSheet("""
                QWidget {
                    background-color: #0A192F;
                    color: #FFFFFF;
                }
                QTabWidget::pane {
                    border: 2px solid #FFD700;
                    background-color: #1A1A1A;
                }
                QTabBar::tab {
                    background-color: #0A192F;
                    color: #FFFFFF;
                    padding: 8px 20px;
                    border: 1px solid #FFD700;
                }
                QTabBar::tab:selected {
                    background-color: #1A1A1A;
                    color: #FFD700;
                }
            """)

    def create_upgrade_row(self, upgrade, upgrade_type, index):
        """Создает строку с улучшением"""
        widget = QWidget()
        layout = QHBoxLayout(widget)

        level = upgrade[3]
        effect = upgrade[2] * (level + 1)
        cost = self.logic.get_upgrade_cost(upgrade)

        level_idx, level_data = self.logic.get_current_level()
        theme_level = level_data['theme']

        label = QLabel(f"{upgrade[0]} (Ур. {level}) | Эффект: +{effect:.2f} | Стоимость: {cost:.2f}")
        label.setFont(QFont("Arial", 10))

        btn_buy = QPushButton("Купить")
        btn_buy.setFixedWidth(100)
        btn_buy.clicked.connect(lambda: self.buy_upgrade(upgrade_type, index))

        if theme_level == 1:
            btn_style = """
                QPushButton { background-color: #5C2E2E; color: white; border: none; padding: 6px; border-radius: 4px;
            }
                QPushButton:hover { background-color: #8B3A3A; }
                QPushButton:disabled { background-color: #3a2626; color: #666666; }
            """
        elif theme_level in (2,3):
            btn_style = """
                QPushButton { background-color: #C72C41; color: white; border: none; padding: 6px; border-radius: 4px;
            }
                QPushButton:hover { background-color: #F05454; }
                QPushButton:disabled { background-color: #6b2029; color: #888888; }
            """
        else:
            btn_style = """
                QPushButton { 
                    background-color: #F4C10F; 
                    color: #000000; 
                    border: none; 
                    padding: 6px; 
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover { 
                    background-color: #FFD700;
                }
                QPushButton:disabled { 
                    background-color: #7a6311; 
                    color: #444444; 
                }
            """

        btn_buy.setStyleSheet(btn_style)

        if self.logic.balance < cost:
            btn_buy.setEnabled(False)

        layout.addWidget(label)
        layout.addWidget(btn_buy)

        if theme_level == 1:
            widget.setStyleSheet("background-color: rgba(30, 30, 40, 0.8); border: 1px solid #45A29E; border-radius: 6px; padding: 8px; margin: 3px;")
        elif theme_level in (2,3):
            widget.setStyleSheet("background-color: #16213E; border: 1px solid #E94560; border-radius: 6px; padding: 8px; margin: 3px;")
        else:
            widget.setStyleSheet("background-color: #1A1A1A; border: 1px solid #FFD700; border-radius: 6px; padding: 8px; margin: 3px;")

        return widget

    def buy_upgrade(self, upgrade_type, index):
        """Обработка покупки улучшения"""
        self.logic.buy_upgrade(upgrade_type, index)
        self.update_shop()
        self.update_callback()

    def update_shop(self):
        """Обновляет все улучшения в магазине"""
        # Очищаем старые виджеты
        while self.passive_layout.count():
            item = self.passive_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
                
        while self.click_layout.count():
            item = self.click_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
                
        while self.level_layout.count():
            item = self.level_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        # Добавляем улучшения
        for i, upgrade in enumerate(self.logic.passive_upgrades):
            self.passive_layout.addWidget(self.create_upgrade_row(upgrade, "passive", i))
        for i, upgrade in enumerate(self.logic.click_upgrades):
            self.click_layout.addWidget(self.create_upgrade_row(upgrade, "click", i))
        for i, upgrade in enumerate(self.logic.level_upgrades):
            self.level_layout.addWidget(self.create_upgrade_row(upgrade, "level", i))

        self.passive_layout.addStretch()
        self.click_layout.addStretch()
        self.level_layout.addStretch()
        
        level_idx, level = self.logic.get_current_level()
        self.update_theme(level['theme'])


class FloatingBonusButton(QPushButton):
    """Кнопка случайного бонуса появляющаяся на экране"""
    def __init__(self, parent, bonus_type, reward):
        super().__init__(parent)
        self.bonus_type = bonus_type
        self.reward = reward
        self.setFixedSize(60, 60)
        self.setStyleSheet("""
            QPushButton {
                border-radius: 30px;
                background-color: #FFD700;
                border: 3px solid #FFA500;
                font-weight: bold;
                color: black;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #FFA500;
            }
        """)
        self.setText("🎁")
        
        # Анимация появления
        self.anim = QPropertyAnimation(self, b"pos")
        self.anim.setDuration(500)
        
        # Таймер исчезновения
        self.kill_timer = QTimer()
        self.kill_timer.timeout.connect(self.deleteLater)
        self.kill_timer.start(4000)


class MainWindow(QMainWindow):
    """Главное окно игры"""

    def __init__(self):
        super().__init__()
        self.logic = CryptoClickerLogic()
        self.shop = None
        self.active_minigame = None
        self.minigame_timer = QTimer()
        self.minigame_timer.timeout.connect(self.check_minigame_event)
        self.minigame_timer.start(1000)
        self.init_ui()
        
        # Загружаем сохраненный прогресс
        self.load_progress()
        self.update_interface()

        # Таймер пассивного дохода
        self.timer = QTimer()
        self.timer.timeout.connect(self.passive_tick)
        self.timer.start(1000)

    def keyPressEvent(self, event):
        """Обработка нажатия клавиш"""
        if event.key() == Qt.Key.Key_Space and self.logic.button_challenge_active and self.logic.button_challenge_required == "space":
            self.logic.button_last_success = time.time()
            self.process_valid_click()
            
    def handle_mouse_click(self, event):
        """Обработка кликов мыши по кнопке"""
        if self.logic.button_challenge_active:
            if event.button() == Qt.MouseButton.LeftButton and self.logic.button_challenge_required == "left":
                self.logic.button_last_success = time.time()
                self.process_valid_click()
            elif event.button() == Qt.MouseButton.RightButton and self.logic.button_challenge_required == "right":
                self.logic.button_last_success = time.time()
                self.process_valid_click()
        else:
            if event.button() == Qt.MouseButton.LeftButton:
                self.process_valid_click()
    
    def process_valid_click(self):
        """Обработка валидного клика"""
        self.logic.process_click()
        
        # Проверка мини-игры на клики
        if self.active_minigame and self.active_minigame["type"] == "click_challenge":
            self.active_minigame["current"] += 1
            if self.active_minigame["current"] >= self.active_minigame["target"]:
                self.minigame_countdown.stop()
                duration = random.randint(15, 45)
                self.logic.bonus_click_multiplier += 2.0
                self.logic.bonus_click_expire = max(self.logic.bonus_click_expire, duration)
                self.active_minigame = None
                self.minigame_label.setText("")
                self.show_result(f"✅ ПОБЕДА! Тройной доход за клик на {duration} секунд!")
                
        # Проверка мини-игры на заработок
        if self.active_minigame and self.active_minigame["type"] == "earn_challenge":
            earned = self.logic.balance - self.active_minigame["start_balance"]
            if earned >= self.active_minigame["target"]:
                self.minigame_countdown.stop()
                duration = random.randint(15, 45)
                self.logic.bonus_passive_multiplier += 3.0
                self.logic.bonus_passive_expire = max(self.logic.bonus_passive_expire, duration)
                self.active_minigame = None
                self.minigame_label.setText("")
                self.show_result(f"✅ ПОБЕДА! Четверной пассивный доход на {duration} секунд!")
        
        self.update_interface()

    def init_ui(self):
        self.setWindowTitle("Крипто Кликер")
        self.setMinimumSize(900, 750)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        layout = QVBoxLayout(self.central_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)

        # Заголовок уровня
        self.level_title = QLabel()
        self.level_title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.level_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.level_title)
        
        # Прогресс бар уровня
        self.level_progress = QProgressBar()
        self.level_progress.setFixedHeight(40)
        self.level_progress.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.level_progress.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.level_progress)
        
        # Панель задания смены кнопки
        self.button_challenge_label = QLabel()
        self.button_challenge_label.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        self.button_challenge_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.button_challenge_label.setStyleSheet("color: #FF4444;")
        layout.addWidget(self.button_challenge_label)
        
        # Панель активного задания
        self.minigame_label = QLabel()
        self.minigame_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.minigame_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.minigame_label.setStyleSheet("color: #FFD700;")
        layout.addWidget(self.minigame_label)
        
        # Панель активных бонусов
        self.bonuses_label = QLabel()
        self.bonuses_label.setFont(QFont("Arial", 10))
        self.bonuses_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.bonuses_label)

        # Баланс
        self.balance_label = QLabel()
        self.balance_label.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        self.balance_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.balance_label)

        # Статистика
        self.stats_label = QLabel()
        self.stats_label.setFont(QFont("Arial", 11))
        self.stats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.stats_label)

        # Пространство для кнопки клика
        layout.addStretch()

        # Кнопка клика
        self.click_button = QPushButton()
        self.click_button.setFixedSize(250, 250)
        self.click_button.mousePressEvent = self.handle_mouse_click
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # Виджет для SVG логотипа
        self.coin_icon = QSvgWidget()
        self.coin_icon.setFixedSize(180, 180)

        # Размещаем логотип внутри кнопки
        btn_layout = QVBoxLayout(self.click_button)
        btn_layout.addWidget(self.coin_icon, alignment=Qt.AlignmentFlag.AlignCenter)
        btn_layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(self.click_button, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Панель результата мини-игры
        self.result_label = QLabel()
        self.result_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_label.setStyleSheet("color: #00FF00;")
        layout.addWidget(self.result_label)

        layout.addStretch()

        # Панель кнопок
        buttons_layout = QHBoxLayout()
        
        # Кнопка сохранения
        self.save_button = QPushButton("💾 СОХРАНИТЬ")
        self.save_button.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.save_button.setFixedHeight(45)
        self.save_button.clicked.connect(self.save_progress)
        buttons_layout.addWidget(self.save_button)
        
        # Кнопка магазина
        self.shop_button = QPushButton("🛒 МАГАЗИН")
        self.shop_button.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.shop_button.setFixedHeight(45)
        self.shop_button.clicked.connect(self.open_shop)
        buttons_layout.addWidget(self.shop_button)
        
        # Кнопка сброса
        self.reset_button = QPushButton("🔄 СБРОС")
        self.reset_button.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.reset_button.setFixedHeight(45)
        self.reset_button.clicked.connect(self.reset_progress)
        buttons_layout.addWidget(self.reset_button)
        
        layout.addLayout(buttons_layout)

        self.update_interface()
        self.setFocus()

    def paintEvent(self, event):
        """Рисует градиентный фон окна"""
        painter = QPainter(self)
        rect = self.rect()
        
        level_idx, level = self.logic.get_current_level()
        theme_level = level['theme']

        gradient = QLinearGradient(0, 0, 0, rect.height())

        if theme_level == 1:
            gradient.setColorAt(0, QColor("#0B0C10"))
            gradient.setColorAt(1, QColor("#1F2833"))
        elif theme_level in (2,3):
            gradient.setColorAt(0, QColor("#1E0A2E"))
            gradient.setColorAt(1, QColor("#2D1B4E"))
        else:
            gradient.setColorAt(0, QColor("#0A192F"))
            gradient.setColorAt(1, QColor("#112240"))

        painter.fillRect(rect, gradient)

    def check_minigame_event(self):
        """Проверяет возможность появления мини-игры"""
        if self.active_minigame:
            return
            
        # Проверка на появление задания смены кнопки клика
        if not self.logic.button_challenge_active and random.random() < 0.005:  # 0.5% шанс каждую секунду
            buttons = ["left", "right", "space"]
            buttons.remove(self.logic.current_click_button)
            self.logic.button_challenge_required = random.choice(buttons)
            self.logic.button_challenge_active = True
            self.logic.button_challenge_time_left = 60
            self.logic.button_last_success = time.time()
            
        # 3% шанс появления мини-игры каждую секунду
        if random.random() < 0.03:
            game_type = random.randint(1, 3)
            
            if game_type == 1:
                # Случайная плавающая кнопка бонуса
                bonus_btn = FloatingBonusButton(self, "click_bonus", 2.0)
                bonus_btn.clicked.connect(lambda: self.collect_bonus(bonus_btn))
                
                # Случайная позиция
                x = random.randint(50, self.width() - 110)
                y = random.randint(100, self.height() - 150)
                bonus_btn.move(x, y)
                bonus_btn.show()
                
            elif game_type == 2:
                # Мини-игра: накликать 20 кликов за 5 секунд
                self.active_minigame = {
                    "type": "click_challenge",
                    "target": 20,
                    "current": 0,
                    "time_left": 5
                }
                self.minigame_countdown = QTimer()
                self.minigame_countdown.timeout.connect(self.minigame_tick)
                self.minigame_countdown.start(1000)
                
            elif game_type == 3:
                # Мини-игра: заработать 50 монет за 7 секунд
                self.active_minigame = {
                    "type": "earn_challenge",
                    "target": 50,
                    "start_balance": self.logic.balance,
                    "time_left": 7
                }
                self.minigame_countdown = QTimer()
                self.minigame_countdown.timeout.connect(self.minigame_tick)
                self.minigame_countdown.start(1000)

    def collect_bonus(self, btn):
        """Собирает бонус с плавающей кнопки"""
        btn.kill_timer.stop()
        
        bonus_type = random.randint(1,4)
        duration = random.randint(10, 30)
        
        if bonus_type == 1:
            self.logic.bonus_click_multiplier += 1.0
            self.logic.bonus_click_expire = max(self.logic.bonus_click_expire, duration)
            self.show_result(f"✅ Двойной доход за клик на {duration} секунд!")
        elif bonus_type == 2:
            self.logic.bonus_level_multiplier += 1.0
            self.logic.bonus_level_expire = max(self.logic.bonus_level_expire, duration)
            self.show_result(f"✅ Двойной прогресс уровня на {duration} секунд!")
        elif bonus_type == 3:
            self.logic.bonus_passive_multiplier += 2.0
            self.logic.bonus_passive_expire = max(self.logic.bonus_passive_expire, duration)
            self.show_result(f"✅ Тройной пассивный доход на {duration} секунд!")
        else:
            reward = random.randint(50, 500)
            self.logic.balance += reward
            self.show_result(f"✅ Получено {reward} монет!")
            
        btn.deleteLater()
        self.update_interface()
        
    def show_result(self, text):
        """Показывает результат внизу под кнопкой"""
        self.result_label.setText(text)
        QTimer.singleShot(4000, lambda: self.result_label.setText(""))

    def minigame_tick(self):
        """Обновляет таймер мини-игры"""
        if not self.active_minigame:
            return
            
        self.active_minigame["time_left"] -= 1
        
        if self.active_minigame["time_left"] <= 0:
            # Мини-игра закончена
            self.minigame_countdown.stop()
            self.active_minigame = None
            self.minigame_label.setText("")
        else:
            if self.active_minigame["type"] == "click_challenge":
                self.minigame_label.setText(f"⚡ НАКЛИКАЙ {self.active_minigame['target']} РАЗ! ОСТАЛОСЬ: {self.active_minigame['time_left']}с  |  ПРОГРЕСС: {self.active_minigame['current']}/{self.active_minigame['target']}")
            else:
                earned = self.logic.balance - self.active_minigame["start_balance"]
                self.minigame_label.setText(f"💰 ЗАРАБОТАЙ {self.active_minigame['target']} МОНЕТ! ОСТАЛОСЬ: {self.active_minigame['time_left']}с  |  ПРОГРЕСС: {earned:.1f}/{self.active_minigame['target']}")

    def update_interface(self):
        """Обновляет все элементы интерфейса"""
        level_idx, level = self.logic.get_current_level()
        progress = self.logic.get_level_progress()
        theme_level = level['theme']

        # Обновляем внешний вид окна
        self.update()

        # Заголовок уровня
        self.level_title.setText(f"Уровень {level_idx + 1}: {level['name']} {level['icon']}")
        
        # Отображение задания смены кнопки
        if self.logic.button_challenge_active:
            btn_name = ""
            if self.logic.button_challenge_required == "left":
                btn_name = "ЛЕВОЙ КНОПКОЙ МЫШИ"
            elif self.logic.button_challenge_required == "right":
                btn_name = "ПРАВОЙ КНОПКОЙ МЫШИ"
            else:
                btn_name = "КЛАВИШЕЙ ПРОБЕЛ"
            
            time_left = self.logic.button_challenge_time_left
            last_click = int(time.time() - self.logic.button_last_success)
            self.button_challenge_label.setText(f"⚠️ НАЖИМАЙ ТОЛЬКО {btn_name} | ОСТАЛОСЬ: {time_left}с  |  БЕЗДЕЙСТВИЕ: {last_click}/5с")
        else:
            self.button_challenge_label.setText("")
        
        # Активные бонусы
        bonuses = []
        if self.logic.bonus_click_multiplier > 1:
            bonuses.append(f"👆 x{self.logic.bonus_click_multiplier} ({self.logic.bonus_click_expire}с)")
        if self.logic.bonus_level_multiplier > 1:
            bonuses.append(f"📈 x{self.logic.bonus_level_multiplier} ({self.logic.bonus_level_expire}с)")
        if self.logic.bonus_passive_multiplier > 1:
            bonuses.append(f"⏱ x{self.logic.bonus_passive_multiplier} ({self.logic.bonus_passive_expire}с)")
        self.bonuses_label.setText(" | ".join(bonuses))
        
        # Обновляем SVG логотип валюты на кнопке
        svg_path = os.path.join(BASE_DIR, level['svg'])
        self.coin_icon.load(svg_path)
        
        # Прогресс бар
        self.level_progress.setValue(int(progress))
        
        if level_idx < len(self.logic.levels) - 1:
            need_for_next = level["max"] - self.logic.total_clicks
            self.level_progress.setFormat(f"{self.logic.total_clicks} / {level['max']}")
        else:
            self.level_progress.setFormat(f"{self.logic.total_clicks} / МАКСИМУМ")

        # Стилизация прогресс бара и кнопок
        if theme_level == 1:
            self.level_progress.setStyleSheet("""
                QProgressBar {
                    background-color: #2C2C2C;
                    border: 2px solid #45A29E;
                    border-radius: 5px;
                    color: #66FCF1;
                }
                QProgressBar::chunk {
                    background-color: #B97A44;
                    border-radius: 3px;
                }
            """)
            self.click_button.setStyleSheet("""
                QPushButton {
                    border-radius: 125px;
                    background-color: #1F2833;
                    border: 3px solid #45A29E;
                }
                QPushButton:pressed {
                    background-color: #0B0C10;
                }
            """)
            self.save_button.setStyleSheet("""
                QPushButton {
                    background-color: #5C2E2E;
                    color: #C5C6C7;
                    border-radius: 8px;
                    border: 2px solid #45A29E;
                }
                QPushButton:hover {
                    background-color: #8B3A3A;
                }
            """)
            self.shop_button.setStyleSheet("""
                QPushButton {
                    background-color: #5C2E2E;
                    color: #C5C6C7;
                    border-radius: 8px;
                    border: 2px solid #45A29E;
                }
                QPushButton:hover {
                    background-color: #8B3A3A;
                }
            """)
            self.reset_button.setStyleSheet("""
                QPushButton {
                    background-color: #5C2E2E;
                    color: #C5C6C7;
                    border-radius: 8px;
                    border: 2px solid #45A29E;
                }
                QPushButton:hover {
                    background-color: #8B3A3A;
                }
            """)
            self.level_title.setStyleSheet("color: #66FCF1;")
            self.balance_label.setStyleSheet("color: #C5C6C7;")
            self.stats_label.setStyleSheet("color: #C5C6C7;")
            self.bonuses_label.setStyleSheet("color: #FFD700;")

        elif theme_level in (2,3):
            self.level_progress.setStyleSheet("""
                QProgressBar {
                    background-color: #16213E;
                    border: 2px solid #E94560;
                    border-radius: 5px;
                    color: #FFD700;
                }
                QProgressBar::chunk {
                    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0, stop: 0 #F2A900, stop: 1 #F25E00);
                    border-radius: 3px;
                }
            """)
            self.click_button.setStyleSheet("""
                QPushButton {
                    border-radius: 125px;
                    background-color: #2D1B4E;
                    border: 3px solid #E94560;
                }
                QPushButton:pressed {
                    background-color: #1E0A2E;
                }
            """)
            self.save_button.setStyleSheet("""
                QPushButton {
                    background-color: #C72C41;
                    color: #FFB347;
                    border-radius: 8px;
                    border: 2px solid #E94560;
                }
                QPushButton:hover {
                    background-color: #F05454;
                }
            """)
            self.shop_button.setStyleSheet("""
                QPushButton {
                    background-color: #C72C41;
                    color: #FFB347;
                    border-radius: 8px;
                    border: 2px solid #E94560;
                }
                QPushButton:hover {
                    background-color: #F05454;
                }
            """)
            self.reset_button.setStyleSheet("""
                QPushButton {
                    background-color: #C72C41;
                    color: #FFB347;
                    border-radius: 8px;
                    border: 2px solid #E94560;
                }
                QPushButton:hover {
                    background-color: #F05454;
                }
            """)
            self.level_title.setStyleSheet("color: #FFD700;")
            self.balance_label.setStyleSheet("color: #FFB347;")
            self.stats_label.setStyleSheet("color: #FFB347;")
            self.bonuses_label.setStyleSheet("color: #FFFFFF;")

        else:
            self.level_progress.setStyleSheet("""
                QProgressBar {
                    background-color: #1A1A1A;
                    border: 2px solid #FFD700;
                    border-radius: 5px;
                    color: #FFFFFF;
                }
                QProgressBar::chunk {
                    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0, 
                        stop: 0 #FFD700, stop: 0.5 #E0115F, stop: 1 #FFD700);
                    border-radius: 3px;
                }
            """)
            self.click_button.setStyleSheet("""
                QPushButton {
                    border-radius: 125px;
                    background-color: #0A192F;
                    border: 3px solid #FFD700;
                }
                QPushButton:pressed {
                    background-color: #112240;
                }
            """)
            self.save_button.setStyleSheet("""
                QPushButton {
                    background-color: #F4C10F;
                    color: #000000;
                    border-radius: 8px;
                    border: 2px solid #FFD700;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #FFD700;
                }
            """)
            self.shop_button.setStyleSheet("""
                QPushButton {
                    background-color: #F4C10F;
                    color: #000000;
                    border-radius: 8px;
                    border: 2px solid #FFD700;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #FFD700;
                }
            """)
            self.reset_button.setStyleSheet("""
                QPushButton {
                    background-color: #F4C10F;
                    color: #000000;
                    border-radius: 8px;
                    border: 2px solid #FFD700;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #FFD700;
                }
            """)
            self.level_title.setStyleSheet("color: #FFD700;")
            self.balance_label.setStyleSheet("color: #FFFFFF;")
            self.stats_label.setStyleSheet("color: #FFFFFF;")
            self.bonuses_label.setStyleSheet("color: #FFD700;")

        # Баланс
        self.balance_label.setText(f"Заработано: {self.logic.balance:.1f} {level['name']}")

        # Статистика с учетом активных бонусов
        effective_click = self.logic.click_power * self.logic.bonus_click_multiplier
        effective_passive = self.logic.passive_income * self.logic.bonus_passive_multiplier
        effective_level = self.logic.click_per_level * self.logic.bonus_level_multiplier
        
        stats_text = f"""
        Доход за клик: {effective_click:.2f}        Пассивный доход: {effective_passive:.2f}/сек

        Сила клика: +{effective_level:.0f} к прогрессу
        """
        self.stats_label.setText(stats_text)

        if self.shop is not None and self.shop.isVisible():
            self.shop.update_shop()

    def passive_tick(self):
        """Обработка тика таймера"""
        self.logic.process_passive_income()
        
        # Проверка окончания задания смены кнопки
        if self.logic.button_challenge_active and self.logic.button_challenge_time_left <= 0:
            self.logic.button_challenge_active = False
            self.logic.current_click_button = self.logic.button_challenge_required
            
        self.update_interface()
        self.setFocus()

    def save_progress(self):
        """Сохраняет прогресс игры в файл"""
        save_data = {
            "balance": self.logic.balance,
            "total_clicks": self.logic.total_clicks,
            "click_power": self.logic.click_power,
            "passive_income": self.logic.passive_income,
            "click_per_level": self.logic.click_per_level,
            "passive_upgrades": [u[3] for u in self.logic.passive_upgrades],
            "click_upgrades": [u[3] for u in self.logic.click_upgrades],
            "level_upgrades": [u[3] for u in self.logic.level_upgrades]
        }
        
        save_path = os.path.join(BASE_DIR, "save.json")
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(save_data, f, indent=2)
        
        QMessageBox.information(self, "Сохранение", "Прогресс успешно сохранен!")

    def load_progress(self):
        """Загружает сохраненный прогресс при запуске"""
        save_path = os.path.join(BASE_DIR, "save.json")
        if os.path.exists(save_path):
            try:
                with open(save_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                self.logic.balance = data.get("balance", 0.0)
                self.logic.total_clicks = data.get("total_clicks", 0)
                self.logic.click_power = data.get("click_power", 1.0)
                self.logic.passive_income = data.get("passive_income", 0.0)
                self.logic.click_per_level = data.get("click_per_level", 1.0)
                
                for i, level in enumerate(data.get("passive_upgrades", [])):
                    self.logic.passive_upgrades[i][3] = level
                for i, level in enumerate(data.get("click_upgrades", [])):
                    self.logic.click_upgrades[i][3] = level
                for i, level in enumerate(data.get("level_upgrades", [])):
                    self.logic.level_upgrades[i][3] = level
                    
            except Exception:
                pass

    def reset_progress(self):
        """Сбрасывает весь прогресс игры"""
        reply = QMessageBox.question(self, "Сброс прогресса", 
                                    "Вы действительно хотите сбросить весь прогресс? Это действие нельзя отменить.",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            self.logic.__init__()
            save_path = os.path.join(BASE_DIR, "save.json")
            if os.path.exists(save_path):
                os.remove(save_path)
            self.update_interface()
            QMessageBox.information(self, "Сброс", "Прогресс сброшен!")

    def open_shop(self):
        """Открывает окно магазина"""
        if self.shop is None or not self.shop.isVisible():
            self.shop = ShopWindow(self.logic, self.update_interface)
        level_idx, level = self.logic.get_current_level()
        self.shop.update_theme(level['theme'])
        self.shop.show()
        self.shop.activateWindow()
    
    def closeEvent(self, event):
        """Обработка закрытия окна игры"""
        reply = QMessageBox.question(self, "Выход из игры", 
                                    "Вы действительно хотите выйти из игры?\nНе забудьте сохранить прогресс!",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            event.accept()
        else:
            event.ignore()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
