import logging
import logs.client_log_config
import argparse
import sys
from PyQt6.QtWidgets import QApplication
from client.client_DB import ClientStorage
from common.variables import *
from errors import ServerError
from client.transport import ClientTransport
from client.main_window import ClientMainWindow
from client.start_dialog import UserNameDialog
from logs.client_log_config import log

# Инициализация клиентского логера
logger = log

# Основная функция клиента
if __name__ == '__main__':

    # Обработка параметров коммандной строки
    try:
        server_address = sys.argv[1]
        server_port = int(sys.argv[2])
        client_name = sys.argv[3]
        if 1024 > server_port > 65535:
            raise ValueError
    except IndexError:
        server_address = DEFAULT_IP_ADDRESS
        server_port = DEFAULT_PORT
        client_name = None
    except ValueError:
        logger.error('Номер порт должен находиться в диапазоне  [1024 - 65535]')
        print('Номер порт должен находиться в диапазоне  [1024 - 65535]')
        sys.exit(1)

    # Создаём клиентcкое приложение
    client_app = QApplication(sys.argv)

    # Если имя пользователя не было указано в командной строке то запросим его
    if not client_name:
        client_name = input('fdfdf')
        # start_dialog = UserNameDialog()
        # start_dialog.exec()
        # Если пользователь ввёл имя и нажал ОК, то сохраняем ведённое и удаляем объект, иначе выходим
        # if start_dialog.ok_pressed:
        #     client_name = start_dialog.client_name.text()
        #     del start_dialog
        # else:
        #     exit(0)

    # Записываем логи
    logger.info(
        f'Запущен клиент с парамертами: адрес сервера: {server_address} , порт: {server_port},'
        f'имя пользователя: {client_name}')

    # Создаём объект базы данных
    database_client = ClientStorage(client_name)
    database_client.init()

    # Создаём объект - транспорт и запускаем транспортный поток
    try:
        transport = ClientTransport(server_port, server_address, database_client, client_name)
    except ServerError as error:
        transport = None
        print(error.text)
        exit(1)
    transport.setDaemon(True)
    transport.start()

    # Создаём GUI
    main_window = ClientMainWindow(database_client, transport)
    main_window.make_connection(transport)
    main_window.setWindowTitle(f'Чат Программа alpha release - {client_name}')
    client_app.exec()

    # Раз графическая оболочка закрылась, закрываем транспорт
    transport.transport_shutdown()
    transport.join()