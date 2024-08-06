import argparse
import socket
import sys
import threading
import time
import queue

from asdetector.utils.logging import get_request_message, request_sendall
from asdetector.utils.files import load_settings

parser = argparse.ArgumentParser()
parser.add_argument('COMMAND', type=str, nargs='+')


def add_input(input_queue):
    while True:
        input_queue.put(sys.stdin.read(1))


class MySocket:
    """demonstration class only
      - coded for clarity, not efficiency
    """

    def __init__(self, sock=None):
        if sock is None:
            self.sock = socket.socket(
                            socket.AF_INET, socket.SOCK_STREAM)
        else:
            self.sock = sock

    def connect(self, host, port):
        self.sock.connect((host, port))

    def mysend(self, msg):
        totalsent = 0
        MSGLEN = len(msg)
        while totalsent < MSGLEN:
            sent = self.sock.send(msg[totalsent:])
            if sent == 0:
                raise RuntimeError("socket connection broken")
            totalsent = totalsent + sent

    def myreceive(self):
        chunks = []
        bytes_recd = 0
        MSGLEN = 60
        while bytes_recd < MSGLEN:
            chunk = self.sock.recv(min(MSGLEN - bytes_recd, 2048))
            if chunk == b'':
                raise RuntimeError("socket connection broken")
            chunks.append(chunk)
            bytes_recd = bytes_recd + len(chunk)
        return b''.join(chunks)

    def receive_beef(self):
        complete = False
        while not complete:
            message = get_request_message(self.sock)
            if message == '\x03' or message == '\x15':
                complete = True
            else:
                print(message)

    def send_beef(self, message):
        request_sendall(self.sock, message)


def main():
    ms = MySocket()
    ms.connect(load_settings()['HOST'], load_settings()['PORT'])
    input_queue = queue.Queue()

    input_thread = threading.Thread(target=add_input, args=(input_queue,))
    input_thread.daemon = True
    input_thread.start()

    last_update = time.time()
    command = ''
    while True:
        if time.time()-last_update > 0.5:
            # sys.stdout.write(".")
            last_update = time.time()

        if not input_queue.empty():
            while not input_queue.empty():
                command += input_queue.get_nowait()
            if command.endswith('\n'):
                print("\ninput:", command)
                ms.send_beef(command)
                ms.receive_beef()
                command = ''


# ms = MySocket()
# ms.connect(load_settings()['HOST'], load_settings()['PORT'])
# ms.mysend(str.encode('TEST'))
# print(ms.myreceive().decode())
# args = parser.parse_args()
# args_joined = (' '.join(args.COMMAND))
# commands = args_joined.split(',')

# for command in commands:
#     ms.send_beef(command)
#     ms.receive_beef()

# foobar()
main()
