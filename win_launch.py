"""Лаунчер"""

import subprocess
from time import sleep

PROCESS = []

while True:
    ACTION = input('Выберите действие: q - выход, '
                   's - запустить сервер и 2 клиентов, x - закрыть все окна: ')

    if ACTION == 'q':
        break
    elif ACTION == 's':
        PROCESS.append(subprocess.Popen('python server.py',
                                        creationflags=subprocess.CREATE_NEW_CONSOLE))
        # LISTENERS
        # for i in range(5):
        sleep(5)
        # PROCESS.append(subprocess.Popen('python client.py',
        #                                 creationflags=subprocess.CREATE_NEW_CONSOLE))
        # sleep(1)
        # PROCESS.append(subprocess.Popen('python client.py',
        #                                 creationflags=subprocess.CREATE_NEW_CONSOLE))
        # SENDERS
        sleep(1)
        for i in range(2):

            PROCESS.append(subprocess.Popen('python client.py',
                                            creationflags=subprocess.CREATE_NEW_CONSOLE))

    elif ACTION == 'x':
        while PROCESS:
            VICTIM = PROCESS.pop()
            VICTIM.kill()
