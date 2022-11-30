import socket
import time
import threading
from PyQt6.QtCore import pyqtSignal, QObject
from common.utils import *
from errors import ServerError, IncorrectDataRecivedError
from logs.client_log_config import log

# Объект блокировки для работы с сокетом
socket_lock = threading.Lock()
# Инициализация клиентского логера
logger = log
sys.path.append('../')


# Класс - Транспорт, отвечает за взаимодействие с сервером
class ClientTransport(threading.Thread, QObject):
    # Сигналы новое сообщение и потеря соединения
    new_message = pyqtSignal(str)
    connection_lost = pyqtSignal()

    def __init__(self, port, ip_address, database_client, account_name):
        # Вызываем конструктор предка
        threading.Thread.__init__(self)
        QObject.__init__(self)

        # Класс База данных - работа с базой
        self.database_client = database_client
        # Имя пользователя
        self.account_name = account_name
        # Сокет для работы с сервером
        self.transport = None
        # self.sock = self.transport
        # Устанавливаем соединение:
        self.connection_init(port, ip_address)
        # Обновляем таблицы известных пользователей и контактов
        try:
            check = self.database_client.check_user(self.account_name)
            if not check:
                database_client.load_users_from_server(self.account_name)
            self.database_client.user_list_client()
            self.database_client.contacts_list()
        except OSError as err:
            if err.errno:
                logger.critical(f'Потеряно соединение с сервером.')
                raise ServerError('Потеряно соединение с сервером!')
            logger.error('Timeout соединения при обновлении списков пользователей.')
        except json.JSONDecodeError:
            logger.critical(f'Потеряно соединение с сервером.')
            raise ServerError('Потеряно соединение с сервером!')
            # Флаг продолжения работы транспорта.
        self.running = True

    # Функция инициализации соединения с сервером
    def connection_init(self, port, ip):
        # Инициализация сокета и сообщение серверу о нашем появлении
        self.transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Таймаут необходим для освобождения сокета.
        self.transport.settimeout(5)

        # Соединяемся, 5 попыток соединения, флаг успеха ставим в True если удалось
        connected = False
        for i in range(5):
            logger.info(f'Попытка подключения №{i + 1}')
            try:
                self.transport.connect((ip, port))
            except (OSError, ConnectionRefusedError):
                pass
            else:
                connected = True

                break
            time.sleep(1)

        # Если соединится не удалось - исключение
        if not connected:
            logger.critical('Не удалось установить соединение с сервером')
            raise ServerError('Не удалось установить соединение с сервером')

        logger.debug('Установлено соединение с сервером')

        # Посылаем серверу приветственное сообщение и получаем ответ что всё нормально или ловим исключение.
        try:
            with socket_lock:
                send_message(self.transport, self.make_presence(self.transport, self.account_name))
                message = get_message(self.transport)
                self.response_process(message)
        except (OSError, json.JSONDecodeError):
            logger.critical('Потеряно соединение с сервером!')
            raise ServerError('Потеряно соединение с сервером!')

        # Раз всё хорошо, сообщение об установке соединения.
        logger.info('Соединение с сервером успешно установлено.')

    # Функция, генерирующая приветственное сообщение для сервера
    @staticmethod
    def make_presence(sock, account_name):
        # if not account_name:
        #     account_name = input('Введите имя пользователя: ')
        logger.debug('Сформировано сообщение серверу')
        # Генерация запроса о присутствии клиента
        data = {
            'action': 'presence',
            'time': time.time(),
            'type': 'status',
            'user': {
                "account_name": account_name,
                "sock": sock.getsockname(),
            }
        }
        return data

    def response_process(self,message):
            if 'response' in message:
                # print(message['response'])
                if message['response'] == 200 and message['data']:
                    print(f'\nПолучено сообщение от клиента {message["login"]}\n {message["data"]}')
                    if message['data'] == f'Вы отправили сообщение не существующему либо отключенному ' \
                                          f'адресату {message["to"]}':
                        print(message['data'])
                        pass
                    else:
                        self.database_client.save_message(message["login"], self.account_name, message["data"])
                        print('111')
                        self.new_message.emit(message['login'])
                        print('2222')
                if message['response'] == 202:
                    print(f'\n {message}')
                if message['response'] == 205:
                    print(f'\n {message}')
                if message['response'] == 210:
                    print(f'\n {message}')

                logger.info('Bad request 400')
            logger.info('Ошибка чтения данных')


    def create_message(self, to, message):
        message_dict = {
            'action': 'message',
            'time': time.time(),
            'user': {
                'account_name': self.account_name,
                'sock': self.transport.getsockname(),
            },
            'to': to,
            'message_text': message
        }
        logger.debug(f'Сформирован словарь сообщения: {message_dict}')
        return message_dict

    # Функция обрабатывающяя сообщения от сервера. Ничего не возращает. Генерирует исключение при ошибке.
    #     def process_server_ans(self, message):
    #         logger.debug(f'Разбор сообщения от сервера: {message}')
    #
    #         # Если это подтверждение чего-либо
    #         if RESPONSE in message:
    #             if message[RESPONSE] == 200:
    #                 return
    #             elif message[RESPONSE] == 400:
    #                 raise ServerError(f'{message[ERROR]}')
    #             else:
    #                 logger.debug(f'Принят неизвестный код подтверждения {message[RESPONSE]}')
    #
    #         # Если это сообщение от пользователя добавляем в базу, даём сигнал о новом сообщении
    #         elif ACTION in message and message[ACTION] == MESSAGE and SENDER in message and DESTINATION in message \
    #                 and MESSAGE_TEXT in message and message[DESTINATION] == self.username:
    #             logger.debug(f'Получено сообщение от пользователя {message[SENDER]}:{message[MESSAGE_TEXT]}')
    #             self.database_client.save_message(message[SENDER], 'in', message[MESSAGE_TEXT])
    #             self.new_message.emit(message[SENDER])

    def create_exit_message(self):
        """Функция создаёт словарь с сообщением о выходе"""
        return {
            'action': 'exit',
            'time': time.time(),
            'user': {
                'account_name': self.account_name,
                'sock': self.transport.getsockname()
            },
        }

    def create_user_contacts_message(self):
        logger.debug('Сформировано запрос серверу на получение списка контактов')
        # Генерация запроса о присутствии клиента
        data = {
            'action': 'get_contacts',
            'time': time.time(),
            'user': {
                "account_name": self.account_name,
                "sock": self.transport.getsockname(),
            }
        }
        return data

    def add_user_contacts_message(self, contact_name):
        data = {
            'action': 'add_contact',
            'time': time.time(),
            'user': {
                "account_name": self.account_name,
                "sock": self.transport.getsockname(),
            },
            'contact': contact_name
        }
        logger.debug(f'Сформировано запрос серверу на добавление контакта {contact_name} пользователю'
                     f' {self.account_name}')
        # self.database_client.add_contact(self.account_name, contact_name)
        return data

    def del_user_contacts_message(self, contact_name):
        data = {
            'action': 'del_contact',
            'time': time.time(),
            'user': {
                "account_name": self.account_name,
                "sock": self.transport.getsockname(),
            },
            'contact': contact_name
        }
        logger.debug(f'Сформировано запрос серверу на удаление контакта {contact_name} пользователя'
                     f' {self.account_name}')

        return data

    # Функция сообщающая на сервер о добавлении нового контакта
    def add_contact_transport(self, contact_name):
        logger.debug(f'Создание контакта {contact_name}')
        req = self.add_user_contacts_message(contact_name)
        logger.debug(f'Сформировано запрос серверу на добавление контакта {contact_name} пользователю'
                     f' {self.account_name}')
        with socket_lock:
            send_message(self.transport, req)
            message = get_message(self.transport)
            self.response_process(message)
            if message['response'] == 205:
                self.database_client.add_contact(contact_name)

    # Функция удаления клиента на сервере
    def remove_contact(self, contact_name):
        logger.debug(f'Удаление контакта {contact_name}')
        req = self.del_user_contacts_message(contact_name)
        logger.debug(f'Сформировано запрос серверу на удаление контакта {contact_name} пользователю'
                     f' {self.account_name}')
        with socket_lock:
            send_message(self.transport, req)
            message = get_message(self.transport)
            self.response_process(message)
            if message['response'] == 210:
                self.database_client.del_contact(contact_name)
        # logger.debug(f'Удаление контакта {contact}')
        # req = self.del_user_contacts_message(contact)
        # with socket_lock:
        #     send_message(self.transport, req)
        #     self.response_process()

    # Функция закрытия соединения, отправляет сообщение о выходе.
    def transport_shutdown(self):
        self.running = False
        message = self.create_exit_message()
        with socket_lock:
            try:
                send_message(self.transport, message)
            except OSError:
                pass
        logger.debug('Транспорт завершает работу.')
        time.sleep(0.5)

    # Функция отправки сообщения на сервер
    def send_message(self, to, message):
        message_dict = self.create_message(to, message)

        # Необходимо дождаться освобождения сокета для отправки сообщения
        with socket_lock:
            send_message(self.transport, message_dict)
            print(message_dict)
            self.database_client.save_message(message_dict['user']['account_name'], message_dict['to'], message_dict['message_text'])
            print(f'Послано сообщение {message_dict}')
            # self.response_process()
            # print(self.response_process())
            logger.info(f'Отправлено сообщение для пользователя {to}')

    def run(self):
        logger.debug('Запущен процесс - приёмник собщений с сервера.')
        while self.running:
            # Отдыхаем секунду и снова пробуем захватить сокет.
            # если не сделать тут задержку, то отправка может достаточно долго ждать освобождения сокета.
            time.sleep(1)
            with socket_lock:
                try:
                    self.transport.settimeout(1)
                    message = get_message(self.transport)
                    print(f'принято сообщение {message}')
                    if 'response' in message:
                        # print(message['response'])
                        if message['response'] == 200 and message['data']:
                            print(f'\nПолучено сообщение от клиента {message["login"]}\n {message["data"]}')
                            if message['data'] == f'Вы отправили сообщение не существующему либо отключенному ' \
                                                  f'адресату {message["to"]}':
                                continue
                            else:
                                self.database_client.save_message(message['login'],message["to"], message["data"])
                                self.new_message.emit(message['login'])
                        if message['response'] == 202:
                            print(f'\n {message}')
                        if message['response'] == 205:
                            print(f'\n {message}')
                        if message['response'] == 210:
                            print(f'\n {message}')
                        logger.info('Bad request 400')
                    logger.info('Ошибка чтения данных')
                except OSError as err:
                    if err.errno:
                        logger.critical(f'Потеряно соединение с сервером.')
                        self.running = False
                        self.connection_lost.emit()
                    # Проблемы с соединением
                except (ConnectionError, ConnectionAbortedError, ConnectionResetError, json.JSONDecodeError, TypeError):
                    logger.debug(f'Потеряно соединение с сервером.')
                    self.running = False
                    self.connection_lost.emit()
                    # Если сообщение получено, то вызываем функцию обработчик:
                else:
                    logger.debug(f'Принято сообщение с сервера: {message}')
                    # self.response_process()
                finally:
                    self.transport.settimeout(5)
