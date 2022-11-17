import dis
import sys
import json
import socket
import threading
import time
from pprint import pprint

from common.variables import DEFAULT_IP_ADDRESS, DEFAULT_PORT
from common.utils import get_message, send_message
import logging
from errors import IncorrectDataRecivedError, ReqFieldMissingError, ServerError

logger = logging.getLogger('client')


class ClientVerifier(type):
    # Вызывается для создания экземпляра класса, перед вызовом __init__
    def __init__(cls, future_class_name, future_class_parents, future_class_attrs):
        """
          Метод проверяет наличие атрибутов из списка required_attributes.
          По умолчанию - ни один из обязательных атрибутов не найден
          (изначально список not_found_attributes == required_attributes).
        """
        super().__init__(type)
        # pprint(cls.__dict__)
        # pprint(future_class_attrs)
        # required_attributes = ['sock', 'account_name']
        # not_found_attributes = required_attributes.copy()
        # for attr, v in future_class_attrs.items():
        #     if attr in required_attributes:
        #         not_found_attributes.remove(attr)

        # if not_found_attributes:
        #     print(not_found_attributes)
            # raise AttributeError(f"Not found attributes: {not_found_attributes}")


        # super(ClientVerifier, cls).__init__(future_class_name,
        #                                     future_class_parents,
        #                                     future_class_attrs)
        # pprint(cls.__dict__)
        for func in cls.__dict__:
            try:
                ret = dis.get_instructions(cls.__dict__[func])
            except TypeError:
                # print(func)
                pass
            else:
                for i in ret:
                    if i.argval in ['accept', 'listen']:
                        raise ValueError(f'Недопуcтимый метод {i.argval}')
                    pprint(i.argval)

                    # print(i.argval)


class ClientSender(threading.Thread, metaclass=ClientVerifier):
    def __init__(self, sock, account_name):
        self.account_name = account_name
        self.sock = sock
        super().__init__()

    def create_exit_message(self):
        """Функция создаёт словарь с сообщением о выходе"""
        return {
            'action': 'exit',
            'time': time.time(),
            'user': {
                "account_name": self.account_name,
                "status": "Yep, I am here!"
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

    def user_interactive(self):
        # s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        """Функция взаимодействия с пользователем, запрашивает команды, отправляет сообщения"""
        print('Поддерживаемые команды:')
        print('message - отправить сообщение. Кому и текст будет запрошены отдельно.')
        print('help - вывести подсказки по командам')
        print('exit - выход из программы')

        while True:
            command = input('Введите команду: ')
            if command == 'message':
                res = self.create_message()
                send_message(self.sock, res)
            elif command == 'help':
                print('Help yourself with yourself')
            elif command == 'exit':
                send_message(self.sock, self.create_exit_message())
                print('Завершение соединения.')
                logger.info('Завершение работы по команде пользователя.')
                # Задержка неоходима, чтобы успело уйти сообщение о выходе
                time.sleep(0.5)
                break
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


class ClientListener(threading.Thread):
    def __init__(self, sock, account_name):
        self.account_name = account_name
        self.sock = sock
        super().__init__()

    def run(self):
        while True:
            try:
                message = get_message(self.sock)
                if 'response' in message:
                    if message['response'] == 200 and message['data']:
                        print(f'\nПолучено сообщение от клиента {message["login"]}\n {message["data"]}')
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

        # receiver = threading.Thread(target=message_from_server, args=(s,))
        receiver = ClientListener(s, answer['login'])
        receiver.daemon = True
        receiver.start()

        # затем запускаем отправку сообщений и взаимодействие с пользователем.
        # user_interface = threading.Thread(target=user_interactive, args=(s, answer["login"]))
        user_interface = ClientSender(s, answer['login'])
        user_interface.user_interactive()
        user_interface.daemon = True
        user_interface.start()
        # user_interface.join()
        logger.debug('Запущены процессы')
        while True:
            time.sleep(1)
            if receiver.is_alive() and user_interface.is_alive():
                continue
            break


if __name__ == '__main__':
    main_client()
