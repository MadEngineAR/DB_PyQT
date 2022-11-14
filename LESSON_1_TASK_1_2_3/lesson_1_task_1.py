"""
1. Написать функцию host_ping(), в которой с помощью утилиты ping будет проверяться доступность сетевых узлов.
Аргументом функции является список, в котором каждый сетевой узел должен быть представлен именем хоста
или ip-адресом. В функции необходимо перебирать ip-адреса и проверять их доступность с выводом соответствующего
сообщения («Узел доступен», «Узел недоступен»). При этом ip-адрес сетевого узла должен создаваться
с помощью функции ip_address().
"""

from ipaddress import ip_address  # https://docs.python.org/3/howto/ipaddress.html#ip-host-addresses
import subprocess
import platform
import threading

param = '-n' if platform.system().lower() == 'windows' else '-c'


def host_ping(url):
    # Проверка на правильность указания ip.
    try:
        ip = ip_address(url)
        args = ['ping', param, '2', ip.compressed]
    except ValueError:
        args = ['ping', param, '2', str(url)]

    process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    process.communicate()
    # print(process)
    if process.returncode == 0:
        print(f'Узел {url} -  Доступен')
    else:
        print(f'Узел {url} -  Недоступен')


# Запуск потоков
def start_thread(args):
    for url in args:
        print(url)
        ping = threading.Thread(target=host_ping, args=(url,))
        ping.start()
        ping.join()


if __name__ == '__main__':
    urls = (input('Введите имя хоста или ip-адрес, через запятую, если требуется проверка '
                  'нескольких адресов\n')).replace(' ', '').split(',')
    print(urls)
    start_thread(urls)
