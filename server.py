"""Программа Сервер. Используется идея:
При регистрации на сервер, Имя Пользователя И адрес его Сокета записываются в слдоварь, и добавляются в
глобальный список USERS. Отправка сообщения происходит при совпадении адреса Сокета и текущего Клиента"""
import dis
import socket
import sys
from pprint import pprint

from my_socket import MySocket
from select import select
from common.variables import ACTION, ACCOUNT_NAME, RESPONSE, MAX_CONNECTIONS, \
    PRESENCE, TIME, USER, ERROR, DEFAULT_PORT
from common.utils import get_message, send_message
import logging

logger = logging.getLogger('server')
users = []


class ServerVerifier(type):
    # Вызывается для создания экземпляра класса, перед вызовом __init__
    def __init__(cls, future_class_name, future_class_parents, future_class_attrs):
        """
          Метод проверяет наличие атрибутов из списка required_attributes.
          По умолчанию - ни один из обязательных атрибутов не найден
          (изначально список not_found_attributes == required_attributes).
        """
        super().__init__(type)
        # pprint(cls.__dict__)
        pprint(future_class_attrs)
        required_attributes = ['sock', 'account_name']
        not_found_attributes = required_attributes.copy()
        for attr, v in future_class_attrs.items():
            if attr in required_attributes:
                not_found_attributes.remove(attr)

        if not_found_attributes:
            print(not_found_attributes)
            # raise AttributeError(f"Not found attributes: {not_found_attributes}")

        # super(ClientVerifier, cls).__init__(future_class_name,
        #                                     future_class_parents,
        #                                     future_class_attrs)
        pprint(cls.__dict__)
        for func in cls.__dict__:
            try:
                ret = dis.get_instructions(cls.__dict__[func])
            except TypeError:
                print(func)
                pass
            else:
                for i in ret:
                    pprint(i.argval)
                    # print(i)


class Server(metaclass=ServerVerifier):
    def __init__(self, listen_address, listen_port):
        # Параметры подключения
        self.addr = listen_address
        self.port = listen_port
        # Список подключенных клиентов
        self.clients = []
        self.clients_socket_names = []
        # Список сообщений
        self.messages = []

    @staticmethod
    def process_client_message(message):
        global users
        logger.debug(f'Получено сообщение от клиента {message}')
        if ACTION in message and message[ACTION] == PRESENCE and TIME in message \
                and USER in message and message[USER][ACCOUNT_NAME]:
            msg = {RESPONSE: 200}
            logger.info(f'Соединение с клиентом: НОРМАЛЬНОЕ {msg}')
            if message[USER] not in users:
                users.append(message[USER])
            print(users)
            return {
                RESPONSE: 200,
                'data': None,
                'login': message['user']['account_name'],
                'sock': message['user']['sock']
            }
        elif ACTION in message and message[ACTION] == 'message' and TIME in message \
                and USER in message and message[USER][ACCOUNT_NAME]:
            return {
                RESPONSE: 200,
                'data': message['message_text'],
                'login': message['user']['account_name'],
                'to': message['to'],
                'sock_address': [user['sock'] for user in users if user['account_name'] == message['to']]
            }
        elif ACTION in message and message[ACTION] == 'exit' and TIME in message \
                and USER in message and message[USER][ACCOUNT_NAME]:
            return {RESPONSE: 200,
                    'data': None,
                    'login': message['user']['account_name'],
                    'sock': message['user']['sock']
                    }
        msg = {
            RESPONSE: 400,
            ERROR: 'Bad Request'
        }
        logger.error(f'Bad request 400', msg)
        return {
            RESPONSE: 400,
            ERROR: 'Bad Request'
        }

    def main_server(self):
        """
        Загрузка параметров командной строки, если нет параметров, то задаём значения по умолчанию.
        Сначала обрабатываем порт:
        server.py -p 8888 -a 127.0.0.1
        """
        logger.info(f'PORT : {self.port} ,IP_ADDRESS {self.addr}')
        s = MySocket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((self.addr, self.port))
        s.listen(MAX_CONNECTIONS)
        s.settimeout(2)
        # clients = []
        # clients_socket_names = []
        # messages = []
        global users
        while True:
            try:
                client, client_address = s.accept()
            except OSError as e:
                print(e.errno)
            else:
                self.clients.append(client)
                self.clients_socket_names.append(client.getpeername())

                print(self.clients_socket_names)
            finally:
                recv_data_lst = []
                send_data_lst = []
                # Проверяем на наличие ждущих клиентов
                try:
                    if self.clients:
                        recv_data_lst, send_data_lst, err_lst = select(self.clients, self.clients, [], 0)
                except OSError:
                    pass

                # принимаем сообщения и если ошибка, исключаем клиента.
                if recv_data_lst:
                    for client_with_message in recv_data_lst:
                        try:
                            message_from_client = get_message(client_with_message)
                            if message_from_client['action'] == 'exit':
                                client_with_message.close()
                                recv_data_lst.remove(client_with_message)
                                send_data_lst.remove(client_with_message)
                            self.messages.append(message_from_client)
                            self.process_client_message(message_from_client)
                        except Exception:
                            logger.info(f'Клиент {client_with_message.getpeername()} '
                                        f'отключился от сервера.')
                            client_with_message.close()
                            # recv_data_lst.remove(client_with_message)
                            # send_data_lst.remove(client_with_message)
                            self.clients.remove(client_with_message)

                # Если есть сообщения, обрабатываем каждое.
                if send_data_lst and self.messages:
                    for message in self.messages:
                        print(message)
                        self.messages.remove(message)
                        for s_listener in send_data_lst:
                            if s_listener.getpeername() in self.clients_socket_names \
                                    and s_listener.getpeername() == tuple(message['user']['sock']) \
                                    and message['action'] == 'presence':
                                try:
                                    response = self.process_client_message(message)
                                    send_message(s_listener, response)
                                except BrokenPipeError:
                                    print('Вах')
                                    send_data_lst.remove(s_listener)
                                except KeyError:
                                    self.clients.remove(s_listener)
                                    pass
                            elif s_listener.getpeername() in self.clients_socket_names and message[
                                'action'] == 'message':
                                try:
                                    response = self.process_client_message(message)
                                    print(response)

                                    if len(response['sock_address']) == 0 \
                                            and s_listener.getpeername() == tuple(message['user']['sock']):
                                        response[
                                            'data'] = f'Вы отправили сообщение не существующему адресату {message["to"]}'
                                        send_message(s_listener, response)
                                    elif s_listener.getpeername() == tuple(response['sock_address'][0]):
                                        send_message(s_listener, response)
                                        print('1111')
                                except BrokenPipeError:
                                    print('Вах')
                                    send_data_lst.remove(s_listener)
                                except IndexError:
                                    pass


def start():
    try:
        if '-p' in sys.argv:
            listen_port = int(sys.argv[sys.argv.index('-p') + 1])
            logger.info(f'PORT : {listen_port}')
            print(sys.argv)
        else:
            listen_port = DEFAULT_PORT
        if 1024 > listen_port > 65535:
            raise ValueError
    except IndexError:
        logger.error('После параметра -\'p\' необходимо указать номер порта.')
        print('После параметра -\'p\' необходимо указать номер порта.')
        sys.exit(1)
    except ValueError:
        logger.error('Номер порт должен находиться в диапазоне  [1024 - 65535]')
        print('Номер порт должен находиться в диапазоне  [1024 - 65535]')
        sys.exit(1)

    # Затем загружаем какой адрес слушать

    try:
        if '-a' in sys.argv:
            listen_address = sys.argv[sys.argv.index('-a') + 1]
        else:
            listen_address = ''
    except IndexError:
        logger.error('После параметра -\'a\' необходимо указать номер порта.')
        print(
            'После параметра \'a\'- необходимо указать адрес')
        sys.exit(1)

    server = Server(listen_address, listen_port)
    server.main_server()


if __name__ == '__main__':
    start()
