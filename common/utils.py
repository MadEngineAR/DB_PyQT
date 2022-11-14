"""Утилиты"""
import sys
import json
import logging
import traceback

from common.variables import MAX_PACKAGE_LENGTH, ENCODING

"""Простейший декоратор-класс"""


class Log:
    """Класс-декоратор"""
    def __call__(self, func):
        def decorated(*args, **kwargs):
            """Обертка"""
            res = func(*args, **kwargs)
            script = sys.argv[0].split('/')[-1]
            function_call = repr(traceback.extract_stack()[1]).split(' ')[-1].strip('>')
            if script == 'client.py':
                # traceback.print_stack()
                # print(function_call)
                logger = logging.getLogger('client')
                logger.info(f'Функция {func.__name__} вызвана из функции {function_call}')
                logger.debug(f'client: {func.__name__}({args}, {kwargs})')
                # print(f'client: {func.__name__}({args}, {kwargs}) = {res}')
            elif script == 'server.py':
                print(function_call)
                logger = logging.getLogger('server')
                logger.debug(f'server: {func.__name__}({args}, {kwargs})')
                logger.info(f'Функция {func.__name__} вызвана из функции {function_call}')
            return res
        return decorated


@Log()
def get_message(client):
    """
    Утилита приёма и декодирования сообщения.
    Принимает байты, выдаёт словарь, если принято что-то
    другое возвращает ValueError (ошибку значения)
    """

    encoded_response = client.recv(MAX_PACKAGE_LENGTH)
    if isinstance(encoded_response, bytes):
        json_response = encoded_response.decode(ENCODING)
        if isinstance(json_response, str):
            response = json.loads(json_response)
            if isinstance(response, dict):
                return response
            raise ValueError
        raise ValueError
    raise ValueError


@Log()
def send_message(sock, message):
    """
    Утилита кодирования и отправки сообщения:
    принимает для отправки словарь, получает из него строку,
    далее превращает строку в байты и отправляет.
    """
    if not isinstance(message, dict):
        raise TypeError
    js_message = json.dumps(message)
    encoded_message = js_message.encode(ENCODING)

    sock.send(encoded_message)
