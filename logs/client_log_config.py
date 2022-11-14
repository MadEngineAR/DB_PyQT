import logging

# Создать логер - регистратор верхнего уровня
# с именем app.main
import os


log = logging.getLogger('client')

# Создать обработчик
PATH = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(PATH, 'client.log')
file_hand = logging.FileHandler(PATH, encoding='utf-8')
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


