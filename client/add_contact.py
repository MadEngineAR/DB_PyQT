import sys
sys.path.append('../')
from PyQt6.QtWidgets import QDialog, QLabel, QComboBox, QPushButton
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QStandardItemModel, QStandardItem
from logs.client_log_config import log


# Инициализация клиентского логера
logger = log


# Диалог выбора контакта для добавления
class AddContactDialog(QDialog):
    def __init__(self, transport, database):
        super().__init__()
        self.transport = transport
        self.database = database

        self.setFixedSize(350, 120)
        self.setWindowTitle('Выберите контакт для добавления:')
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setModal(True)

        self.selector_label = QLabel('Выберите контакт для добавления:', self)
        self.selector_label.setFixedSize(200, 20)
        self.selector_label.move(10, 0)

        self.selector = QComboBox(self)
        self.selector.setFixedSize(200, 20)
        self.selector.move(10, 30)

        self.btn_refresh = QPushButton('Обновить список', self)
        self.btn_refresh.setFixedSize(100, 30)
        self.btn_refresh.move(60, 60)

        self.btn_ok = QPushButton('Добавить', self)
        self.btn_ok.setFixedSize(100, 30)
        self.btn_ok.move(230, 20)

        self.btn_cancel = QPushButton('Отмена', self)
        self.btn_cancel.setFixedSize(100, 30)
        self.btn_cancel.move(230, 60)
        self.btn_cancel.clicked.connect(self.close)

        # Заполняем список возможных контактов
        self.possible_contacts_update()
        # Назначаем действие на кнопку обновить
        self.btn_refresh.clicked.connect(self.update_possible_contacts)

    # Заполняем список возможных контактов разницей между всеми пользователями и
    def possible_contacts_update(self):
        self.selector.clear()
        # множества всех контактов и контактов клиента
        contacts_list = set(self.database.contacts_list())
        users_cont= set(self.database.user_list_client())
        users_list = users_cont - contacts_list
        # print(users_list)
        # Удалим сами себя из списка пользователей, чтобы нельзя было добавить самого себя
        # print(self.database.user_list_client(self.transport.account_name)[0])
        try:
            self.database.user_list_client(self.transport.account_name)[0]
        except IndexError:
            self.database.user_list_client()
        user = self.database.user_list_client(self.transport.account_name)[0]
        users_list.remove(user)
        # print(users_list)
        # print(users_list - contacts_list)
        possible_contact_list = []
        for item in users_list:
            possible_contact_list.append(item[1])
        # Добавляем список возможных контактов
        self.selector.addItems(possible_contact_list)

    # Обновлялка возможных контактов. Обновляет таблицу известных пользователей,
    # затем содержимое предполагаемых контактов
    def update_possible_contacts(self):
        try:
            self.transport.user_list_update()
        except OSError:
            pass
        else:
            logger.debug('Обновление списка пользователей с сервера выполнено')
            self.possible_contacts_update()
