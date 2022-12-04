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
        try:
            PROCESS.append(subprocess.Popen('python server_PyQT.py', stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                                        creationflags=subprocess.CREATE_NEW_CONSOLE))
        except Exception as e:
            print(e)


        # Clients
        sleep(1)

        for i in range(2):
            proc = subprocess.Popen('python client_PyQT.py',
                                            creationflags=subprocess.CREATE_NEW_CONSOLE)
            PROCESS.append(proc)
            print(PROCESS)

    elif ACTION == 'x':
        while PROCESS:
            VICTIM = PROCESS.pop()
            VICTIM.kill()
