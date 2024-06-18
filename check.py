import requests
import random
import threading
import socket
import struct

def generate_random_ip():
    return socket.inet_ntoa(struct.pack('>I', random.randint(1, 0xffffffff)))

def check(proxy):
    url = 'http://httpbin.org/ip'
    proxies = {
        'http': f'http://{proxy}',
        'https': f'http://{proxy}'
    }
    try:
        response = requests.get(url, proxies=proxies, timeout=10)
        if response.status_code == 200:
            return True
        else:
            return True
    except Exception as e:
        return False

def Main():
    while True:
        ports = [8888,80,8080,8000,443,8443,4433,9080,4145,8081,999,3128,8181,6666]
        for port in ports:
            ip = generate_random_ip()
            proxy = ip + ":" + str(port)
            if check(proxy):
                print(f'Found Working Proxy! {proxy}')
                with open("working.txt", 'a') as file:
                    file.write(proxy + '\n')
            else:
                print(f'Failed Proxy: {proxy}')

if __name__ == "__main__":
    num_threads = 1000
    threads = []
    for _ in range(num_threads):
        thread = threading.Thread(target=Main)
        thread.start()
        threads.append(thread)
