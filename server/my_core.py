"""Программа Сервер. Используется идея:
При регистрации на сервер, Имя Пользователя И адрес его Сокета записываются в словарь, и добавляются в
глобальный список USERS. Отправка сообщения происходит при совпадении адреса Сокета и текущего Клиента"""
import binascii
import datetime
import hmac
import os
import socket
import threading
from PyQt6.QtCore import pyqtSignal, QObject
from select import select
from common.descriptor import NonNegative
from my_socket import MySocket
from common.utils import get_message, send_message
from logs.server_log_config import log
from common.variables import *

logger = log
users = []


class Server(threading.Thread, QObject):
    port = NonNegative()
    new_connection = pyqtSignal()

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
        threading.Thread.__init__(self)
        QObject.__init__(self)

    def process_client_message(self, message, client):
        global users
        # print(message)
        logger.debug(f'Получено сообщение от клиента {message}')
        if ACTION in message and message[ACTION] == PRESENCE and TIME in message \
                and USER in message and message[USER][ACCOUNT_NAME]:
            res_auth = self.autorize_user(message, client)
            if res_auth != RESPONSE_400:
                username = message[USER][ACCOUNT_NAME]
                ip_address = message['user']['sock'][0]
                port = message['user']['sock'][1]
                self.database.user_login(username, ip_address, port)
                self.new_connection.emit()
                users.append(message[USER])
                # self.service_update_lists()
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
            res = sorted(self.database.contacts_list(username))
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
            res_all = sorted(self.database.user_list())
            for item in res_all:
                if item.username == contact_name:
                    return {
                        RESPONSE: 205
                    }

        elif ACTION in message and message[ACTION] == 'del_contact' and TIME in message \
                and USER in message and message[USER][ACCOUNT_NAME]:
            contact_name = message['contact']
            res_all = sorted(self.database.user_list())
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

    def remove_client(self, client):
        """
        Метод обработчик клиента с которым прервана связь.
        Ищет клиента и удаляет его из списков и базы:
        """
        logger.info(f'Клиент {client.getpeername()} отключился от сервера.')
        for user in users:
            if user['account_name'] == client:
                users.remove(user)
                break
        self.clients.remove(client)
        client.close()

    def autorize_user(self, message, sock):
        """Метод реализующий авторизцию пользователей."""
        # Если имя пользователя уже занято то возвращаем 400
        logger.debug(f'Start auth process for {message[USER]}')

        # Проверяем что пользователь зарегистрирован на сервере.
        if not self.database.check_user(message[USER][ACCOUNT_NAME]):
            response = RESPONSE_400
            response[ERROR] = 'Пользователь не зарегистрирован.'
            try:
                logger.debug(f'Unknown username, sending {response}')
                send_message(sock, response)
            except OSError:
                pass
            self.clients.remove(sock)
            sock.close()
        else:
            logger.debug('Correct username, starting passwd check.')
            # Иначе отвечаем 511 и проводим процедуру авторизации
            # Словарь - заготовка
            message_auth = RESPONSE_511
            # Набор байтов в hex представлении
            random_str = binascii.hexlify(os.urandom(64))
            # В словарь байты нельзя, декодируем (json.dumps -> TypeError)
            message_auth[DATA] = random_str.decode('ascii')
            # Создаём хэш пароля и связки с рандомной строкой, сохраняем
            # серверную версию ключа
            hash_ = hmac.new(self.database.get_hash(message[USER][ACCOUNT_NAME]), random_str, 'MD5')
            digest = hash_.digest()
            logger.debug(f'Auth message = {message_auth}')
            try:
                # Обмен с клиентом
                send_message(sock, message_auth)
                ans = get_message(sock)
            except OSError as err:
                logger.debug('Error in auth, data:', exc_info=err)
                sock.close()
                return
            client_digest = binascii.a2b_base64(ans[DATA])
            # Если ответ клиента корректный, то сохраняем его в список
            # пользователей.
            if RESPONSE in ans and ans[RESPONSE] == 511 and hmac.compare_digest(
                    digest, client_digest):
                try:
                    send_message(sock, RESPONSE_200)
                except OSError:
                    self.remove_client(message[USER][ACCOUNT_NAME])

            else:
                response = RESPONSE_400
                response[ERROR] = 'Неверный пароль.'
                try:
                    send_message(sock, response)
                except OSError:
                    pass
                self.clients.remove(sock)
                sock.close()
                return RESPONSE_400

    def service_update_lists(self):
        """Метод реализующий отправки сервисного сообщения 205 клиентам"""
        for client in self.clients:
            try:
                send_message(client, RESPONSE_215)
            except OSError:
                self.clients.remove(client)

    def run(self):
        """
        Загрузка параметров командной строки, если нет параметров, то задаём значения по умолчанию.
        Сначала обрабатываем порт:
        server_PyQT.py -p 8888 -a 127.0.0.1
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
                print(e.errno)
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

                            print(message_from_client)
                            if message_from_client['action'] == 'exit':
                                recv_data_lst.remove(client_with_message)
                                send_data_lst.remove(client_with_message)
                                self.clients.remove(client_with_message)
                                self.clients_socket_names.remove(client_with_message.getpeername())
                                users.remove(message_from_client[USER])

                            else:
                                self.messages.append(message_from_client)
                                print(self.messages)
                                self.process_client_message(message_from_client, client_with_message)
                        except Exception:
                            logger.info(f'Клиент {client_with_message.getpeername()} '
                                        f'отключился от сервера.')
                            client_with_message.close()
                            self.clients.remove(client_with_message)

                # Если есть сообщения, обрабатываем каждое.
                if send_data_lst and self.messages:
                    for message in self.messages:
                        self.messages.remove(message)
                        for s_listener in send_data_lst:
                            try:
                                if s_listener.getpeername() in self.clients_socket_names \
                                        and s_listener.getpeername() == tuple(message['user']['sock']) \
                                        and (message['action'] == 'presence' or message['action'] == 'get_contacts' or
                                             message['action'] == 'add_contact' or message['action'] == 'del_contact'):
                                    try:
                                        if message['action'] == 'add_contact':
                                            response = self.process_client_message(message, s_listener)
                                            send_message(s_listener, response)
                                            message[
                                                'message_text'] = f'Added to {message[USER][ACCOUNT_NAME]} contact list'
                                            self.database.contact(message[USER][ACCOUNT_NAME], message['contact'],
                                                                  datetime.datetime.now(),
                                                                  message['message_text']
                                                                  )
                                        elif message['action'] == 'del_contact':
                                            response = self.process_client_message(message, s_listener)
                                            # print(response)
                                            send_message(s_listener, response)
                                            message[
                                                'message_text'] = f'Deleted from {message[USER][ACCOUNT_NAME]}' \
                                                                  f' contact list'
                                            self.database.del_contact(message[USER][ACCOUNT_NAME], message['contact'],
                                                                      datetime.datetime.now(),
                                                                      message['message_text'])
                                    except BrokenPipeError:
                                        print('Вах')
                                        send_data_lst.remove(s_listener)
                                    except KeyError:
                                        self.clients.remove(s_listener)
                                        pass
                                elif s_listener.getpeername() in self.clients_socket_names and \
                                        message['action'] == 'message':
                                    try:
                                        response = self.process_client_message(message, s_listener)
                                        print(response)
                                        if len(response['sock_address']) == 0 \
                                                and s_listener.getpeername() == tuple(message['user']['sock']):
                                            response[
                                                'data'] = f'Вы отправили сообщение не существующему либо отключенному '\
                                                          f'адресату {message["to"]}'
                                            send_message(s_listener, response)
                                        elif s_listener.getpeername() == tuple(response['sock_address']):
                                            send_message(s_listener, response)

                                            print(response)
                                            self.database.contact(message[USER][ACCOUNT_NAME], message['to'],
                                                                  datetime.datetime.now(), message['message_text'])
                                    except BrokenPipeError:
                                        print('Вах')
                                        send_data_lst.remove(s_listener)
                                    except IndexError:
                                        pass
                            except OSError:
                                pass
