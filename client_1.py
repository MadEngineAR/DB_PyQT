import dis
import sys
import json
import socket
import threading
import time

from common.variables import DEFAULT_IP_ADDRESS, DEFAULT_PORT
from common.utils import get_message, send_message
from logs.client_log_config import log
from errors import IncorrectDataRecivedError, ReqFieldMissingError, ServerError
from server import database
from client_DB import ClientStorage

logger = log


class ClientVerifier(type):
    # Вызывается для создания экземпляра класса, перед вызовом __init__
    def __new__(mcs, name, bases, dict):
        new_class = super(ClientVerifier, mcs).__new__(mcs, name, bases, dict)
        # print(f'__new__({name}, {bases}, {dict}) -> {new_class}')
        return new_class

    def __init__(cls, future_class_name, future_class_parents, future_class_attrs):
        """
          Метод проверяет наличие запрещенных методов .
        """
        super().__init__(type)
        for func in cls.__dict__:
            try:
                ret = dis.get_instructions(cls.__dict__[func])
            except TypeError:
                pass
            else:
                for i in ret:
                    if i.argval in ['accept', 'listen']:
                        raise ValueError(f'Недопуcтимый метод {i.argval}')
                    if i.argval == 'socket':
                        raise ValueError(f'Недопуcтимо создание сокета внутри класса')

    def __call__(cls, *args, **kwargs):
        """
            Проверка на тип сокета. При создании экземпляра класса ClientSender, СlientListener - маг.метод проверяет
            переданный сокет, в качестве атрибута при создании.
            __call__() вызывается при создании объектов класса;
        """
        obj = super(ClientVerifier, cls).__call__(*args, **kwargs)
        sock = args[0]
        if 'SOCK_STREAM' in str(sock.type):
            pass
        else:
            raise ValueError('Не допустимый тип сокета')
        return obj


class ClientSender(threading.Thread, metaclass=ClientVerifier):
    def __init__(self, sock, account_name, database_client):
        self.account_name = account_name
        self.sock = sock
        self.database_client = database_client
        super().__init__()

    def create_exit_message(self):
        """Функция создаёт словарь с сообщением о выходе"""
        return {
            'action': 'exit',
            'time': time.time(),
            'user': {
                'account_name': self.account_name,
                'sock': self.sock.getsockname()
            },
        }

    def create_message(self):
        """Функция запрашивает текст сообщения и возвращает его.
        Так же завершает работу при вводе подобной комманды
        """

        message = input('Введите сообщение для отправки: ')
        to = input('Введите получателя(-ей) сообщения: ')
        message_dict = {
            'action': 'message',
            'time': time.time(),
            'user': {
                'account_name': self.account_name,
                'sock': self.sock.getsockname(),
            },
            'to': to,
            'message_text': message
        }
        logger.debug(f'Сформирован словарь сообщения: {message_dict}')
        return message_dict

    def create_user_contacts_message(self):
        logger.debug('Сформировано запрос серверу на получение списка контактов')
        # Генерация запроса о присутствии клиента
        data = {
            'action': 'get_contacts',
            'time': time.time(),
            'user': {
                "account_name": self.account_name,
                "sock": self.sock.getsockname(),
            }
        }
        return data

    def add_user_contacts_message(self, contact_name):
        contact_list = []
        res = sorted(database.contacts_list(self.account_name))
        for item in res:
            if item.contact_name not in contact_list:
                contact_list.append(item.contact_name)
        if not contact_name:
            contact_name = input('Введите имя контакта: ')
            while True:
                contact_is_register = sorted(database.user_list(contact_name))
                if contact_name not in contact_list:
                    if contact_is_register:
                        data = {
                            'action': 'add_contact',
                            'time': time.time(),
                            'user': {
                                "account_name": self.account_name,
                                "sock": self.sock.getsockname(),
                            },
                            'contact': contact_name
                        }
                        logger.debug(f'Сформировано запрос серверу на добавление контакта {contact_name} пользователю'
                                     f' {self.account_name}')
                        self.database_client.add_contact(self.account_name, contact_name)
                        return data
                    print(f'Вы указали не зарегистрированного пользователя {contact_name}')
                    contact_name = input('Введите имя контакта: ')
                elif contact_name in contact_list:
                    print('Данный пользователь уже в вашем списке контактов')
                    break

                else:
                    print(f'Вы указали не зарегистрированного пользователя {contact_name}')
                    break

    def del_user_contacts_message(self, contact_name):
        contact_list = []
        res = sorted(database.contacts_list(self.account_name))
        for item in res:
            if item.contact_name not in contact_list:
                contact_list.append(item.contact_name)
        if not contact_name:
            contact_name = input('Введите имя контакта: ')
            while True:
                contact_is_register = sorted(database.user_list(contact_name))
                if contact_name in contact_list:
                    if contact_is_register:
                        data = {
                            'action': 'del_contact',
                            'time': time.time(),
                            'user': {
                                "account_name": self.account_name,
                                "sock": self.sock.getsockname(),
                            },
                            'contact': contact_name
                        }
                        logger.debug(f'Сформировано запрос серверу на удаление контакта {contact_name} пользователя'
                                     f' {self.account_name}')
                        self.database_client.del_contact(self.account_name, contact_name)
                        return data
                    else:
                        print(f'Вы указали не зарегистрированного пользователя {contact_name}')
                        contact_name = input('Введите имя контакта: ')
                elif contact_name not in contact_list and contact_is_register:
                    print('Данный пользователь не состоит в вашем списке контактов')
                    break

                else:
                    print(f'Вы указали не зарегистрированного пользователя {contact_name}')
                    contact_name = input('Введите имя контакта: ')

    def user_interactive(self):
        #    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        """Функция взаимодействия с пользователем, запрашивает команды, отправляет сообщения"""
        print('Поддерживаемые команды:')
        print('message - отправить сообщение. Кому и текст будет запрошены отдельно.')
        print('help - вывести подсказки по командам')
        print('exit - выход из программы')
        print('get_contacts - получение списка контактов(только клиентов, которым писал пользователь)')
        print('add_contact - добавление контакта')
        print('del_contact - удаление контакта')
        print('history - история сообщений')
        while True:
            command = input('Введите команду: ')
            if command == 'message':
                res = self.create_message()
                send_message(self.sock, res)
                if self.database_client.user_list_client(res['to']):
                    self.database_client.save_message(self.account_name, res['to'], res['message_text'])
            elif command == 'get_contacts':
                res = self.create_user_contacts_message()
                send_message(self.sock, res)
            elif command == 'add_contact':
                res = self.add_user_contacts_message(None)
                try:
                    send_message(self.sock, res)
                except TypeError:
                    continue
            elif command == 'del_contact':
                res = self.del_user_contacts_message(None)
                try:
                    send_message(self.sock, res)
                except TypeError:
                    continue
            elif command == 'help':
                print('Help yourself with yourself')
            elif command == 'exit':
                send_message(self.sock, self.create_exit_message())
                print('Завершение соединения.')
                logger.info('Завершение работы по команде пользователя.')
                # Задержка неоходима, чтобы успело уйти сообщение о выходе
                time.sleep(0.5)
                break
            elif command == 'history':
                self.database_client.get_history(self.account_name, self.account_name)
            else:
                print('Команда не распознана, попробуйте снова. help - вывести поддерживаемые команды.')


def make_presence(sock, account_name):
    if not account_name:
        account_name = input('Введите имя пользователя: ')
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


class ClientListener(threading.Thread, metaclass=ClientVerifier):
    def __init__(self, sock, account_name, database_client):
        self.account_name = account_name
        self.sock = sock
        self.database_client = database_client
        super().__init__()

    def run(self):
        while True:
            try:
                message = get_message(self.sock)
                if 'response' in message:
                    # print(message['response'])
                    if message['response'] == 200 and message['data']:
                        print(f'\nПолучено сообщение от клиента {message["login"]}\n {message["data"]}')
                        if message['data'] == f'Вы отправили сообщение не существующему либо отключенному ' \
                                f'адресату {message["to"]}':
                            continue
                        else:
                            self.database_client.save_message(message["login"], self.account_name, message["data"])
                    if message['response'] == 202:
                        print(f'\n {message}')
                    if message['response'] == 205:
                        print(f'\n {message}')
                    if message['response'] == 210:
                        print(f'\n {message}')
                    logger.info('Bad request 400')
                logger.info('Ошибка чтения данных')
            except (IncorrectDataRecivedError, ValueError):
                logger.error(f'Не удалось декодировать полученное сообщение.')
            except (OSError, ConnectionError, ConnectionAbortedError,
                    ConnectionResetError, json.JSONDecodeError):
                logger.critical(f'Потеряно соединение с сервером.')
                print('Потеряно соединение с сервером.')
                break


def response_process(sock):
    try:
        message = get_message(sock)
        if 'response' in message:
            if message['response'] == 200:
                logger.info('Соединение с сервером: нормальное')
                return {'msg': 'На связи', 'login': message['login']}
            logger.warning('Bad request 400')
            return f'Bad request 400'
        logger.error('Ошибка чтения данных')
    except ValueError:
        print('Ошибка чтения данных')


def main_client():
    # Обработка параметров коммандной строки
    try:
        server_address = sys.argv[1]
        server_port = int(sys.argv[2])
        if 1024 > server_port > 65535:
            raise ValueError
    except IndexError:
        server_address = DEFAULT_IP_ADDRESS
        server_port = DEFAULT_PORT
    except ValueError:
        logger.error('Номер порт должен находиться в диапазоне  [1024 - 65535]')
        print('Номер порт должен находиться в диапазоне  [1024 - 65535]')
        sys.exit(1)

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # print(s.family)
        s.connect((server_address, server_port))
        send_message(s, make_presence(s, account_name=None))
        answer = response_process(s)
        logger.info(f'Установлено соединение с сервером. Ответ сервера: {answer["msg"]}')
        print(f'ИМЯ ПОЛЬЗОВАТЕЛЯ: {answer["login"]}')
        print(f'Установлено соединение с сервером.')
    except json.JSONDecodeError:
        logger.error('Не удалось декодировать полученную Json строку.')

        sys.exit(1)
    except ServerError as error:
        logger.error(f'При установке соединения сервер вернул ошибку: {error.text}')
        sys.exit(1)
    except ReqFieldMissingError as missing_error:
        logger.error(f'В ответе сервера отсутствует необходимое поле {missing_error.missing_field}')
        sys.exit(1)
    except (ConnectionRefusedError, ConnectionError):
        logger.critical(
            f'Не удалось подключиться к серверу {server_address}:{server_port}, '
            f'конечный компьютер отверг запрос на подключение.')
        sys.exit(1)
    else:

        database_client = ClientStorage(answer['login'])
        database_client.init()
        receiver = ClientListener(s, answer['login'], database_client)
        receiver.daemon = True
        receiver.start()

        # затем запускаем отправку сообщений и взаимодействие с пользователем.
        user_interface = ClientSender(s, answer['login'], database_client)
        user_interface.user_interactive()
        user_interface.daemon = True
        user_interface.start()
        logger.debug('Запущены процессы')
        while True:
            time.sleep(1)
            if receiver.is_alive() and user_interface.is_alive():
                continue
            break


if __name__ == '__main__':
    main_client()
