import binascii
import hashlib
import hmac
import socket
import time
import threading
from PyQt6.QtCore import pyqtSignal, QObject
from common.utils import *
from common.errors import ServerError
from logs.client_log_config import log
from common.variables import *

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

    def __init__(self, port, ip_address, database_client, account_name, password):
        # Вызываем конструктор предка
        threading.Thread.__init__(self)
        QObject.__init__(self)

        # Класс База данных - работа с базой
        self.database_client = database_client
        # Имя пользователя
        self.account_name = account_name
        # Пароль
        self.password = password

        # Сокет для работы с сервером
        self.transport = None

        # Устанавливаем соединение:
        self.connection_init(port, ip_address)
        # Обновляем таблицы известных пользователей и контактов
        try:
            check = self.database_client.check_user(self.account_name)
            if not check:
                database_client.load_users_from_server(self.account_name)
            self.database_client.user_list_client()
            self.database_client.contacts_list(self.account_name)
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

        # Запускаем процедуру авторизации
        # Получаем хэш пароля
        passwd_bytes = self.password.encode('utf-8')
        salt = self.account_name.lower().encode('utf-8')
        passwd_hash = hashlib.pbkdf2_hmac('sha512', passwd_bytes, salt, 10000)
        passwd_hash_string = binascii.hexlify(passwd_hash)

        # Посылаем серверу приветственное сообщение и получаем ответ, что всё нормально или ловим исключение.
        try:
            with socket_lock:
                send_message(self.transport, self.make_presence())
                ans = get_message(self.transport)
                if RESPONSE in ans:
                    if ans[RESPONSE] == 400:
                        raise ServerError(ans[ERROR])
                    elif ans[RESPONSE] == 511:
                        # Если всё нормально, то продолжаем процедуру
                        # авторизации.
                        ans_data = ans[DATA]
                        hash = hmac.new(passwd_hash_string, ans_data.encode('utf-8'), 'MD5')
                        digest = hash.digest()
                        my_ans = RESPONSE_511
                        my_ans[DATA] = binascii.b2a_base64(
                            digest).decode('ascii')
                        send_message(self.transport, my_ans)
                        ans = get_message(self.transport)
                        if ans[RESPONSE] == 400:
                            raise ServerError(ans[ERROR])
                        # self.response_process(get_message(self.transport))

        except (OSError, json.JSONDecodeError) as err:
                logger.debug(f'Connection error.', exc_info=err)
                raise ServerError('Сбой соединения в процессе авторизации.')
        except (OSError, json.JSONDecodeError):
            logger.critical('Потеряно соединение с сервером!')
            raise ServerError('Потеряно соединение с сервером!')

        # Раз всё хорошо, сообщение об установке соединения.
        logger.info('Соединение с сервером успешно установлено.')

    # Функция, генерирующая приветственное сообщение для сервера

    def make_presence(self):
        # if not account_name:
        #     account_name = input('Введите имя пользователя: ')
        logger.debug('Сформировано сообщение серверу')
        # Генерация запроса о присутствии клиента
        data = {
            'action': 'presence',
            'time': time.time(),
            'type': 'status',
            'user': {
                "account_name": self.account_name,
                "sock": self.transport.getsockname()
            }
        }
        return data

    def response_process(self, message):
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
                        self.new_message.emit(message['login'])
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
            print(req)
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

    def user_list_update(self):
        '''Метод обновляющий с сервера список клиентов'''
        self.database_client.users_clear()
        self.database_client.update_users()

    # def user_contacts_update(self):
    #     '''Метод обновляющий с сервера список клиентов'''
    #     self.database_client.contacts_clear()
    #     self.database_client.update_contacts()

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
                                self.database_client.save_message(message['login'], message["to"], message["data"])
                                self.new_message.emit(message['login'])
                        if message['response'] == 202:
                            print(f'\n {message}')
                        if message['response'] == 205:
                            print(f'\n {message}')
                        if message['response'] == 210:
                            print(f'\n {message}')
                        if message['response'] == 215:
                            self.user_list_update()
                            # self.user_contacts_update()
                        if message['response'] == 400:
                            self.transport.close()
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
