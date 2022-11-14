"""
2. Написать функцию host_range_ping() для перебора ip-адресов из заданного диапазона.
Меняться должен только последний октет каждого адреса. По результатам проверки должно выводиться
соответствующее сообщение.
"""

from ipaddress import ip_address  # https://docs.python.org/3/howto/ipaddress.html#ip-host-addresses
import subprocess
import platform
import threading

param = '-n' if platform.system().lower() == 'windows' else '-c'


def host_ping_range(url):
    args = ['ping', param, '2', url.compressed]
    process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    process.communicate()
    if process.returncode == 0:
        print(f'Узел {url} -  Доступен')
    else:
        print(f'Узел {url} -  Недоступен')


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
                ping = threading.Thread(target=host_ping_range, args=(ip+i,))
                # ping.daemon = True
                ping.start()
                ping.join()
                i += 1
        else:
            print(f'Введен неверный диапазон, допустимое значение при заданном ip {url} - {254 - last}')
            exit(3)
    except ValueError:
        print('Введен не верный ip')
        exit(1)


if __name__ == '__main__':
    params = (input('Ip-адрес и диапазон, через запятую\n')).replace(' ', '').split(',')
    start_thread(params)
