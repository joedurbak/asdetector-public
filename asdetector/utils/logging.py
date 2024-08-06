from __future__ import print_function

# import threading
# import multiprocessing
import traceback
from datetime import datetime as dt
# from socket import socket
from threading import Lock

from asdetector.utils.files import gen_logfile_name, gen_logfile


server_message_start = int(0xbeef).to_bytes(2, 'big')


def request_sendall_bytes(request, bytes_string):
    _start = server_message_start
    _len = len(bytes_string).to_bytes(4, 'big')
    # request.write(_start + _len + bytes_string)
    request.sendall(_start + _len + bytes_string)


def request_sendall(request, string):
    _encoded_string = str(string).encode()
    request_sendall_bytes(request, _encoded_string)


def write_sendall(write, string):
    _encoded_string = str(string).encode()
    write_sendall_bytes(write, _encoded_string)


def write_sendall_bytes(request, bytes_string):
    _start = server_message_start
    _len = len(bytes_string).to_bytes(4, 'big')
    request.write(_start + _len + bytes_string)


class EmptyMessage(Exception):
    pass


def read_tcp_byte(wfile, message_list):
    message_list.append(wfile.read(1))


def get_tcp_message(request, timeout=60):
    message_start = server_message_start
    message_list = []
    start_time = dt.now()
    # _thread = multiprocessing.Process(target=read_tcp_byte, args=(request, message_list))
    # _thread.start()
    # while (dt.now() - start_time).total_seconds() < timeout:
    while True:
        # message_list.append(request.read(1).strip())
        try:
            message_list.append(request.read(1))
        except MemoryError:
            log_and_print("Memory Error, message_list: {}".format(message_list))
            tb = traceback.format_exc()
            raise MemoryError(tb)
        if len(message_list) > 1:
            snippet = message_list[-2:]

            if b''.join(snippet) == message_start:
                print(b"got "+message_start)
                message_length_binary = request.read(4)
                message_length = int.from_bytes(message_length_binary, 'big')
                print("message_length", message_length)
                message = request.read(message_length)
                message_stripped = message.decode().strip()
                if not message_stripped:
                    raise EmptyMessage("Received empty message: {}".format(message))
                return message.decode()
    # _thread.terminate()
    # raise TimeoutError(
    #     "Timeout. Never received start of message code, {}. Received: {}".format(
    #         server_message_start, b''.join(message_list)),
    # )


def get_request_message(request, timeout=60):
    message_start = server_message_start
    message_list = []
    start_time = dt.now()
    while (dt.now() - start_time).total_seconds() < timeout:
        message_list.append(request.recv(1).strip())
        if len(message_list) > 1:
            snippet = message_list[-2:]

            if b''.join(snippet) == message_start:
                message_length_binary = request.recv(4)
                message_length = int.from_bytes(message_length_binary, 'big')
                message = request.recv(message_length)
                return message.decode().strip()
    raise TimeoutError(
        "Timeout. Never received start of message code, {}. Received: {}".format(
            server_message_start, b''.join(message_list)),
    )


class LogPrintHandler:
    def __init__(self):
        self.lock = Lock()

    def log_and_print(self, string, logfile=None, request=None, log=True, verbose=True):
        # self.lock.acquire()
        string = str(string)
        if logfile is None:
            logfile = gen_logfile_name()

        gen_logfile(logfile)
        if log:
            with open(logfile, 'a') as f:
                f.write(dt.isoformat(dt.now()) + '\n' + string + 3 * '\n')
        if verbose:
            print(string)
        string += '\n'
        if request is not None:
            # assert isinstance(request, socket)
            write_sendall(request, string)
        # self.lock.release()

    def error_log_and_print(self, exception, logfile=None, request=None):
        if logfile is None:
            logfile = gen_logfile_name('ERROR')
        self.log_and_print(exception, logfile=logfile, request=request)


def log_and_print(string, logfile=None, request=None, log=True, verbose=True):
    LogPrintHandler().log_and_print(string, logfile, request, log, verbose)


def error_log_and_print(exception, logfile=None, request=None):
    if logfile is None:
        logfile = gen_logfile_name('ERROR')
    log_and_print(exception, logfile=logfile, request=request)
