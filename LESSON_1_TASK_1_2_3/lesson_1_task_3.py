"""
3. Написать функцию host_range_ping_tab(), возможности которой основаны на функции из примера 2.
Но в данном случае результат должен быть итоговым по всем ip-адресам, представленным в табличном формате
(использовать модуль tabulate).
"""

from ipaddress import ip_address  # https://docs.python.org/3/howto/ipaddress.html#ip-host-addresses
import subprocess

import platform
import threading

from tabulate import tabulate

param = '-n' if platform.system().lower() == 'windows' else '-c'
available_hosts = []
disable_hosts = []


def host_ping_range(url):
    args = ['ping', param, '2', url.compressed]
    process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    process.communicate()
    if process.returncode == 0:
        available_hosts.append(url.compressed)
    else:
        disable_hosts.append(url.compressed)


# Запуск потоков
def start_thread(args):
    try:
        args[1]
    except IndexError:
        print(f'Не введен диапазон')
        exit(2)
    interval = int(args[1])
    last = int(args[0][-1])
    # Проверка на правильность указания ip.
    try:
        url = args[0]
        ip = ip_address(url)
        ip_max = ip + interval
        summ = int(args[0][-1]) + int(interval)
        if summ < 255:
            i = 0
            while (ip + i) < ip_max:
                ping = threading.Thread(target=host_ping_range, args=(ip + i,))
                # ping.daemon = True
                ping.start()
                ping.join()
                i += 1
            table = [('Доступные узлы', 'Недоступные узлы'),
                     (available_hosts, disable_hosts),
                     ]

            # Указание первой строки таблицы как набора заголовков
            print(tabulate(table, headers='firstrow', tablefmt="grid"))
        else:
            print(f'Введен неверный диапазон, допустимое значение при заданном ip {url} - {254 - last}')
            exit(3)
    except ValueError:
        print('Введен не верный ip')
        exit(1)


if __name__ == '__main__':
    params = (input('Ip-адрес и диапазон, через запятую\n')).replace(' ', '').split(',')
    start_thread(params)
