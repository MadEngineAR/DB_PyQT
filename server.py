"""Программа Сервер. Используется идея:
При регистрации на сервер, Имя Пользователя И адрес его Сокета записываются в слдоварь, и добавляются в
глобальный список USERS. Отправка сообщения происходит при совпадении адреса Сокета и текущего Клиента"""

import socket
import sys
from my_socket import MySocket
from select import select
from common.variables import ACTION, ACCOUNT_NAME, RESPONSE, MAX_CONNECTIONS, \
    PRESENCE, TIME, USER, ERROR, DEFAULT_PORT
from common.utils import get_message, send_message
import logging

logger = logging.getLogger('server')
users = []


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
        return  {RESPONSE: 200,
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


def main_server():
    """
    Загрузка параметров командной строки, если нет параметров, то задаём значения по умолчанию.
    Сначала обрабатываем порт:
    server.py -p 8888 -a 127.0.0.1
    """

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

    logger.info(f'PORT : {listen_port} ,IP_ADDRESS {listen_address}')
    s = MySocket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((listen_address, listen_port))
    s.listen(MAX_CONNECTIONS)
    s.settimeout(2)
    clients = []
    clients_socket_names = []
    messages = []
    global users
    while True:
        try:
            client, client_address = s.accept()
        except OSError as e:
            print(e.errno)
        else:
            clients.append(client)
            clients_socket_names.append(client.getpeername())

            print(clients_socket_names)
        finally:
            recv_data_lst = []
            send_data_lst = []
            # Проверяем на наличие ждущих клиентов
            try:
                if clients:
                    recv_data_lst, send_data_lst, err_lst = select(clients, clients, [], 0)
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
                        messages.append(message_from_client)
                        process_client_message(message_from_client)
                    except Exception:
                        logger.info(f'Клиент {client_with_message.getpeername()} '
                                    f'отключился от сервера.')
                        client_with_message.close()
                        # recv_data_lst.remove(client_with_message)
                        # send_data_lst.remove(client_with_message)
                        clients.remove(client_with_message)

            # Если есть сообщения, обрабатываем каждое.
            if send_data_lst and messages:
                for message in messages:
                    print(message)
                    messages.remove(message)
                    for s_listener in send_data_lst:
                        if s_listener.getpeername() in clients_socket_names \
                                and s_listener.getpeername() == tuple(message['user']['sock']) \
                                and message['action'] == 'presence':
                            try:
                                response = process_client_message(message)
                                send_message(s_listener, response)
                            except BrokenPipeError:
                                print('Вах')
                                send_data_lst.remove(s_listener)
                            except KeyError:
                                clients.remove(s_listener)
                                pass
                        elif s_listener.getpeername() in clients_socket_names and message['action'] == 'message':
                            try:
                                response = process_client_message(message)

                                if len(response['sock_address']) == 0 \
                                        and s_listener.getpeername() == tuple(message['user']['sock']):
                                    response[
                                        'data'] = f'Вы отправили сообщение не существующему адресату {message["to"]}'
                                    send_message(s_listener, response)
                                elif s_listener.getpeername() == tuple(response['sock_address'][0]):
                                    send_message(s_listener, response)
                            except BrokenPipeError:
                                print('Вах')
                                send_data_lst.remove(s_listener)
                            except IndexError:
                                pass


if __name__ == '__main__':
    main_server()
