import configparser
import threading
from PyQt6.QtWidgets import QMainWindow, QApplication, QLabel, QTableView, QMessageBox
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QAction
from PyQt6.QtCore import QTimer
from server.stat_window import StatWindow
from server.config_window import ConfigWindow
from server.add_user import RegisterUser
from server_qui import gui_create_model, HistoryWindow, create_stat_model

conflag_lock = threading.Lock()
config = configparser.ConfigParser()


class MainWindowServer(QMainWindow):
    '''Класс - основное окно сервера.'''

    def __init__(self, database, server, config):
        # Конструктор предка
        super().__init__()

        # База данных сервера
        self.database = database

        self.server_thread = server
        self.config = config

        self.messages = QMessageBox()

        # Ярлык выхода
        self.exitAction = QAction('Выход', self)
        self.exitAction.setShortcut('Ctrl+Q')

        # Кнопка обновить список клиентов
        self.refresh_button = QAction('Обновить список', self)

        # Кнопка настроек сервера
        self.config_btn = QAction('Настройки сервера', self)

        # Кнопка регистрации пользователя
        self.register_btn = QAction('Регистрация пользователя', self)

        # Кнопка вывести историю сообщений
        self.show_history_button = QAction('История клиентов', self)

        # Статусбар
        self.statusBar()
        self.statusBar().showMessage('Server Working')

        # Тулбар
        self.toolbar = self.addToolBar('MainBar')
        self.toolbar.addAction(self.exitAction)
        self.toolbar.addAction(self.refresh_button)
        self.toolbar.addAction(self.show_history_button)
        self.toolbar.addAction(self.config_btn)
        self.toolbar.addAction(self.register_btn)

        # Настройки геометрии основного окна
        # Поскольку работать с динамическими размерами мы не умеем, и мало
        # времени на изучение, размер окна фиксирован.
        self.setFixedSize(800, 600)
        self.setWindowTitle('Messaging Server alpha release')

        # Надпись о том, что ниже список подключённых клиентов
        self.label = QLabel('Список подключённых клиентов:', self)
        self.label.setFixedSize(240, 15)
        self.label.move(10, 25)

        # Окно со списком подключённых клиентов.
        self.active_clients_table = QTableView(self)
        self.active_clients_table.move(10, 45)
        self.active_clients_table.setFixedSize(780, 400)

        # Таймер, обновляющий список клиентов 1 раз в секунду
        self.timer = QTimer()
        self.timer.timeout.connect(self.list_update)
        self.timer.start(1000)

        # Связываем кнопки с процедурами
        self.refresh_button.triggered.connect(self.list_update)
        self.show_history_button.triggered.connect(self.show_statistics)
        self.config_btn.triggered.connect(self.server_config)
        self.register_btn.triggered.connect(self.reg_user)

        self.statusBar().showMessage('Server Working')
        self.active_clients_table.setModel(gui_create_model(database))
        self.active_clients_table.resizeColumnsToContents()
        self.active_clients_table.resizeRowsToContents()

    def list_update(self):
        with conflag_lock:
            self.active_clients_table.setModel(
                gui_create_model(self.database))
            self.active_clients_table.resizeColumnsToContents()
            self.active_clients_table.resizeRowsToContents()

    # Функция, создающая окно со статистикой клиентов
    def show_statistics(self):
        global stat_window
        stat_window = HistoryWindow()
        stat_window.history_table.setModel(create_stat_model(self.database))
        stat_window.history_table.resizeColumnsToContents()
        stat_window.history_table.resizeRowsToContents()
        stat_window.show()

    # Функция создающяя окно с настройками сервера.
    def server_config(self):
        global config_window
        # Создаём окно и заносим в него текущие параметры
        config_window = ConfigWindow(self.config)

    def reg_user(self):
        '''Метод создающий окно регистрации пользователя.'''
        global reg_window
        reg_window = RegisterUser(self.database, self.server_thread)
        reg_window.show()

    def new_conn(self):
        self.messages.information(self, 'New connection', ' ')
        self.list_update()

    def make_connection(self, server_obj):
        # print(server_obj.new_connection)
        server_obj.new_connection.connect(self.new_conn)
