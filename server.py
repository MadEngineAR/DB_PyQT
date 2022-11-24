"""Программа Сервер. Используется идея:
При регистрации на сервер, Имя Пользователя И адрес его Сокета записываются в словарь, и добавляются в
глобальный список USERS. Отправка сообщения происходит при совпадении адреса Сокета и текущего Клиента"""
import datetime
import dis
import socket
import sys
import threading
from pprint import pprint

from server_DB import ServerStorage
from descriptor import NonNegative
from my_socket import MySocket
from select import select
from common.variables import ACTION, ACCOUNT_NAME, RESPONSE, MAX_CONNECTIONS, \
    PRESENCE, TIME, USER, ERROR, DEFAULT_PORT
from common.utils import get_message, send_message
from logs.server_log_config import log

# logger = logging.getLogger('server')
logger = log
users = []
# Глобальная переменная, переходит в истину если используется socket.type SOCK_STREAM
flag = False
flag_user_valid = False
database = ServerStorage()


class ServerVerifier(type):

    def __init__(cls, future_class_name, future_class_parents, future_class_attrs):
        """
          Метод проверяет наличие запрещенных методов.
        """
        super().__init__(type)
        global flag
        for func in cls.__dict__:
            try:
                ret = dis.get_instructions(cls.__dict__[func])
            except TypeError:
                pass
            else:
                for i in ret:
                    if i.argval == 'connect':
                        raise ValueError(f'Недопуcтимый метод {i.argval}')
                    if i.argval == 'SOCK_STREAM':
                        global flag
                        flag = True
                        print(f'Подключение по TCP: {flag}')

        if not flag:
            raise ValueError('Не допустимый тип сокета')


class Server(threading.Thread, metaclass=ServerVerifier):
    port = NonNegative()

    def __init__(self, listen_address, port, database):
        # Параметры подключения
        self.addr = listen_address
        self.port = port

        # База данных сервера
        self.database = database
        # Список подключенных клиентов
        self.clients = []
        self.clients_socket_names = []
        # Список сообщений
        self.messages = []
        super().__init__()

    def process_client_message(self, message):
        global users
        # print(message)
        logger.debug(f'Получено сообщение от клиента {message}')
        if ACTION in message and message[ACTION] == PRESENCE and TIME in message \
                and USER in message and message[USER][ACCOUNT_NAME]:
            msg = {RESPONSE: 200}
            logger.info(f'Соединение с клиентом: НОРМАЛЬНОЕ {msg}')
            if message[USER] not in users:
                users.append(message[USER])
            self.database.user_login(message[USER][ACCOUNT_NAME], message['user']['sock'][0],
                                     int(message['user']['sock'][1]))
            return {
                RESPONSE: 200,
                'data': None,
                'login': message['user']['account_name'],
                'sock': message['user']['sock']
            }
        elif ACTION in message and message[ACTION] == 'get_contacts' and TIME in message \
                and USER in message and message[USER][ACCOUNT_NAME]:
            username = message[USER][ACCOUNT_NAME]
            alert = []
            res = sorted(database.contacts_list(username))
            for item in res:
                if item.contact_name not in alert:
                    alert.append(item.contact_name)
            # print(alert)
            logger.info(f'Cформирован список контактов клиента {username}')

            return {
                RESPONSE: 202,
                'alert': alert,
                'login': message['user']['account_name'],
                'sock': message['user']['sock']
            }
        elif ACTION in message and message[ACTION] == 'add_contact' and TIME in message \
                and USER in message and message[USER][ACCOUNT_NAME]:
            contact_name = message['contact']
            res_all = sorted(database.user_list())
            for item in res_all:
                if item.username == contact_name:
                    return {
                        RESPONSE: 205
                    }

        elif ACTION in message and message[ACTION] == 'del_contact' and TIME in message \
                and USER in message and message[USER][ACCOUNT_NAME]:
            contact_name = message['contact']
            res_all = sorted(database.user_list())
            for item in res_all:
                if item.username == contact_name:
                    return {
                        RESPONSE: 210
                    }

        elif ACTION in message and message[ACTION] == 'message' and TIME in message \
                and USER in message and message[USER][ACCOUNT_NAME]:
            try:
                sock_address = [user['sock'] for user in users if user['account_name'] == message['to']][0]
            except IndexError:
                sock_address = ''
            # print(sock_address)
            msg = {
                RESPONSE: 200,
                'data': message['message_text'],
                'login': message['user']['account_name'],
                'to': message['to'],
                'sock_address': sock_address
            }
            # print(msg)
            return msg
        elif ACTION in message and message[ACTION] == 'exit' and TIME in message \
                and USER in message and message[USER][ACCOUNT_NAME]:
            users.remove(message[USER])
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

    def run(self):
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
        global users
        while True:
            try:
                client, client_address = s.accept()
            except OSError as e:
                # print(e.errno)
                pass
            else:
                self.clients.append(client)
                self.clients_socket_names.append(client.getpeername())
                # print(self.clients_socket_names)
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
                                # client_with_message.close()
                                recv_data_lst.remove(client_with_message)
                                send_data_lst.remove(client_with_message)
                                self.clients.remove(client_with_message)
                                # print(client_with_message.getpeername())
                                self.clients_socket_names.remove(client_with_message.getpeername())
                                # print(message_from_client[USER])
                                # print(users)

                                users.remove(message_from_client[USER])
                                # print(users)
                            else:
                                self.messages.append(message_from_client)
                                self.process_client_message(message_from_client)
                        except Exception:
                            logger.info(f'Клиент {client_with_message.getpeername()} '
                                        f'отключился от сервера.')
                            client_with_message.close()
                            self.clients.remove(client_with_message)

                # Если есть сообщения, обрабатываем каждое.
                if send_data_lst and self.messages:
                    for message in self.messages:
                        # print(message)
                        self.messages.remove(message)
                        for s_listener in send_data_lst:
                            if s_listener.getpeername() in self.clients_socket_names \
                                    and s_listener.getpeername() == tuple(message['user']['sock']) \
                                    and (message['action'] == 'presence' or message['action'] == 'get_contacts' or
                                         message['action'] == 'add_contact' or message['action'] == 'del_contact'):
                                try:
                                    if message['action'] == 'add_contact':
                                        response = self.process_client_message(message)
                                        # print(response)
                                        send_message(s_listener, response)
                                        message['message_text'] = f'Added to {message[USER][ACCOUNT_NAME]} contact list'
                                        # print(message)
                                        self.database.contact(message[USER][ACCOUNT_NAME], message['contact'],
                                                              datetime.datetime.now(),
                                                              message['message_text']
                                                              )
                                    elif message['action'] == 'del_contact':
                                        response = self.process_client_message(message)
                                        # print(response)
                                        send_message(s_listener, response)
                                        message[
                                            'message_text'] = f'Deleted from {message[USER][ACCOUNT_NAME]} contact list'
                                        self.database.del_contact(message[USER][ACCOUNT_NAME], message['contact'],
                                                                  datetime.datetime.now(),
                                                                  message['message_text'])
                                        # print('yep')
                                    else:
                                        response = self.process_client_message(message)
                                        send_message(s_listener, response)
                                except BrokenPipeError:
                                    print('Вах')
                                    send_data_lst.remove(s_listener)
                                except KeyError:
                                    self.clients.remove(s_listener)
                                    pass
                            elif s_listener.getpeername() in self.clients_socket_names and \
                                    message['action'] == 'message':
                                try:
                                    response = self.process_client_message(message)
                                    # print(response)
                                    if len(response['sock_address']) == 0 \
                                            and s_listener.getpeername() == tuple(message['user']['sock']):
                                        response['data'] = f'Вы отправили сообщение не существующему либо отключенному ' \
                                                           f'адресату {message["to"]}'
                                        send_message(s_listener, response)
                                    elif s_listener.getpeername() == tuple(response['sock_address']):
                                        send_message(s_listener, response)
                                        self.database.contact(message[USER][ACCOUNT_NAME], message['to'],
                                                              datetime.datetime.now(), message['message_text'])
                                        # contacts = self.ClientContacts(user.id, contact_name, contact_time, message,
                                        #                                sender.sender_count,
                                        #                                recipient.recepient_count, is_friend)
                                except BrokenPipeError:
                                    print('Вах')
                                    send_data_lst.remove(s_listener)
                                except IndexError:
                                    pass


def main():
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

    # Передаем базу данных
    global database
    server = Server(listen_address, listen_port, database)
    server.daemon = True
    server.start()

    print('Поддерживаемые команды:')
    print('users - вывод всех известных пользователей')
    print('history - вывод истории подключения клиента(-ов)')
    print('сontacts - вывод списка контактов клиента(-ов)')

    while True:
        command = input('Введите команду: ')
        if command == 'users':
            res = sorted(database.user_list())
            for item in res:
                print(f'Клиент {item.username} подключался с ip {item.ip_address} порта {item.port}'
                      f'дата {item.last_login}')
        elif command == 'help':
            print('Help yourself with yourself')
        elif command == 'exit':
            print('Завершение соединения.')
            logger.info('Завершение работы по команде пользователя.')
            # Задержка необходима, чтобы успело уйти сообщение о выходе
            break
        elif command == 'history':
            username = input('Введите имя пользователя, либо Enter для просмотра истории всех пользователей: ')
            if username:
                res = sorted(database.history(username))
                if not res:
                    print(f'Пользователь {username} не зарегистрирован в системе')
                    continue
                for item in res:
                    print(f'Клиент {username} подключался с ip {item.ip_address} порта {item.port}'
                          f'дата {item.login_time}')
            else:
                res_all = sorted(database.history())
                for item in res_all:
                    print(f'Клиент {item.username} подключался с ip {item.ip_address} порта {item.port}')
        elif command == 'contacts':
            username = input('Введите имя пользователя, либо Enter для просмотра контактов всех пользователей: ')
            if username:
                res = sorted(database.contacts_list(username))
                res_all = sorted(database.history(username))
                if not res and res_all:
                    print(f'Пользователь {username} ни с кем не контактировал')
                elif not res and not res_all:
                    print(f'Пользователь {username} не зарегистрирован в системе')
                    continue
                for item in res:
                    print(f'Клиент {username} имел контакт с {item.contact_name} дата {item.contact_time}')
            else:
                res_all = sorted(database.contacts_list(username=None))
                for item in res_all:
                    print(f'Клиент {item.username} имел контакт с {item.contact_name} дата {item.contact_time}')
        else:
            print('Команда не распознана, попробуйте снова. help - вывести поддерживаемые команды.')


# def user_interactive():
#     """Функция взаимодействия с пользователем, запрашивает команды, отправляет сообщения"""
#     print('Поддерживаемые команды:')
#     print('users - вывод всех известных пользователей')
#     print('history - вывод истории подключения клиента(-ов)')
#     print('сontacts - вывод списка контактов клиента(-ов)')
#
#     while True:
#         command = input('Введите команду: ')
#         if command == 'users':
#             res = sorted(database.user_list())
#             pprint(res)
#         elif command == 'help':
#             print('Help yourself with yourself')
#         elif command == 'exit':
#             print('Завершение соединения.')
#             logger.info('Завершение работы по команде пользователя.')
#             # Задержка неоходима, чтобы успело уйти сообщение о выходе
#             break
#         else:
#             print('Команда не распознана, попробуйте снова. help - вывести поддерживаемые команды.')


if __name__ == '__main__':
    main()
