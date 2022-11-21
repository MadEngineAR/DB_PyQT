import logging
import logging.handlers
# Создать логер - регистратор верхнего уровня
# с именем app.main
import os

log = logging.getLogger('server')

# Создать обработчик
PATH = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(PATH, 'server.log')
file_hand = logging.handlers.TimedRotatingFileHandler(PATH, encoding='utf8', when='midnight')

# выводит сообщения с уровнем DEBUG
file_hand.setLevel(logging.DEBUG)

# Создать объект formatter и задать формат сообщений
formatter = logging.Formatter("%(asctime)s - %(levelname)-8s - %(message)s ")

# подключить объект Formatter к обработчику
file_hand.setFormatter(formatter)

# Добавить обработчик к регистратору
log.addHandler(file_hand)
log.setLevel(logging.DEBUG)

if __name__ == '__main__':
    # Передать сообщение обработчику
    log.debug('Отладочная информация')
    log.info('Информационное сообщение')
    log.warning('Предупреждение')
    log.error('Ошибка')
    log.critical('Критическое общение')
