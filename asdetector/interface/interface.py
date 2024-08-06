from __future__ import print_function

import io
import os
import traceback
from time import sleep
import threading
import signal

from six.moves import socketserver
from contextlib import redirect_stdout

from asdetector.utils.logging import log_and_print, error_log_and_print, get_tcp_message, write_sendall, EmptyMessage
from asdetector.utils.status import Status as StatusReadWrite
# update_current_command, update_command_complete, get_status_str
from asdetector.interface.templates import response
from asdetector.detector import io_open, io_init, io_sync, io_start, io_close, io_config
from asdetector.utils.files import load_settings, save_offsets, load_offsets, update_setting
from asdetector.utils.image import FRAME_REDUCE_METHODS


completion_message = 'Completed request'
stop_threads = False
status = StatusReadWrite()


class ExecutionError(Exception):
    pass


class CloseHandle(Exception):
    pass


class BaseCommand(object):
    def __init__(self, arguments, received_message, status, logfile=None, request=None, *args, **kwargs):
        self.__name__ = self.__class__.__name__
        # print(self.__name__)
        self.command_render_dict = {}
        self.response_template = response.response.get(self.__name__, response.base)
        self.response_render_dict = {'command_name': self.__name__}
        self.arguments = arguments
        self.received_message = received_message
        self.logfile = logfile
        self.request = request
        self.status = status

    def print(self, string):
        log_and_print(string, logfile=self.logfile, request=self.request)

    def response(self):
        return self.response_template.format(**self.response_render_dict)

    def parse_arguments(self):
        pass

    def execute_command(self):
        return self.response()

    def generate_save_name(self):
        return self.__name__


class Open(BaseCommand):
    def __init__(self, *args, **kwargs):
        super(Open, self).__init__(*args, **kwargs)

    def execute_command(self):
        self.print('Starting MACIE software')
        io_open(request=self.request, status=self.status)
        return self.response()


class Init(BaseCommand):
    def __init__(self, *args, **kwargs):
        super(Init, self).__init__(*args, **kwargs)

    def execute_command(self):
        self.print('Initializing hardware')
        io_init(request=self.request, status=self.status)
        return self.response_template.format(**self.response_render_dict)


class Sync(BaseCommand):
    def __init__(self, *args, **kwargs):
        super(Sync, self).__init__(*args, **kwargs)

    def execute_command(self):
        self.print('Syncing detectors')
        io_sync(request=self.request, status=self.status)
        return self.response_template.format(**self.response_render_dict)


class Start(BaseCommand):
    def __init__(self, *args, **kwargs):
        super(Start, self).__init__(*args, **kwargs)
        self.exposure_time = 3
        self.num_exposures = 1
        self.skip_time = 0

    def execute_command(self):
        self.parse_arguments()
        for exposure in range(self.num_exposures):
            # self.print('Exposure {}'.format(exposure+1))
            # self.print('Starting {} second exposure'.format(self.exposure_time))
            io_start(self.exposure_time, skip_time=self.skip_time, request=self.request, status=self.status)
            # sleep(self.exposure_time)
            # self.print('Reading out final frame')
            # self.print('Exposure complete')
        return self.response_template.format(**self.response_render_dict)

    def parse_arguments(self):
        if len(self.arguments) > 0:
            self.exposure_time = float(self.arguments[0])
        else:
            self.exposure_time = float(3)
        if len(self.arguments) > 1:
            self.skip_time = float(self.arguments[1])
        else:
            self.skip_time = 0
        if len(self.arguments) > 2:
            self.num_exposures = int(self.arguments[2])
        else:
            self.num_exposures = int(1)


class Close(BaseCommand):
    def __init__(self, *args, **kwargs):
        super(Close, self).__init__(*args, **kwargs)

    def execute_command(self):
        self.print('Closing MACIE software')
        if not load_settings()['TCPMSGCLOSE']:
            self.request = None
        io_close(status=self.status, request=self.request)
        return self.response()


class Unlock(BaseCommand):
    def __init__(self, *args, **kwargs):
        super(Unlock, self).__init__(*args, **kwargs)
        log_and_print(
            "Unlock command doesn't do anything, you may skip this command in the future", request=self.request
        )


class Config(BaseCommand):
    def __init__(self, *args, **kwargs):
        super(Config, self).__init__(*args, **kwargs)
        self.offsets = []

    def execute_command(self):
        self.parse_arguments()
        self.inspect_offsets()
        save_offsets(self.offsets)
        io_config(request=self.request)

    def parse_arguments(self):
        self.offsets = [
            [int(offset.strip(), 16) for offset in offset_list.split(',')] for offset_list in self.arguments
        ]

    def inspect_offsets(self):
        len_args = len(self.offsets)
        _settings = load_settings()
        num_cams = _settings['NUMBEROFCAMERAS']
        num_offsets = _settings['NUMBEROFREADOUTCHANNELS']
        check_cmd = ' Check command and settings.json'
        extra_off = ' Extra offsets won\'t be loaded.'
        if len_args >= num_cams:
            if len_args > num_cams:
                self.print(
                    'Expected offsets for only {} cameras, but received offsets for {} cameras.'.format(
                        num_cams, len_args) + extra_off + check_cmd
                )
            for offset_list in self.offsets:
                if len(offset_list) < num_offsets:
                    raise SyntaxError(
                        'Should have offsets for at least {} channels, but only have offsets for {} channels.'.format(
                            num_offsets, len(offset_list)) + check_cmd
                    )
                elif len(offset_list) > num_offsets:
                    self.print(
                        'Expected offsets for only {} channels, but received offsets for {} channels.'.format(
                            num_offsets, len(offset_list)) + extra_off + check_cmd
                    )
        else:
            raise SyntaxError(
                'Should have offsets for at least {} cameras, but only have offsets for {} cameras.'.format(
                    num_cams, len_args) + check_cmd
            )


class ConfigFromFile(Config):
    def __init__(self, *args, **kwargs):
        super(ConfigFromFile, self).__init__(*args, **kwargs)

    def parse_arguments(self):
        if len(self.arguments) == 0:
            self.offsets = load_offsets()
        else:
            self.offsets = load_offsets(self.arguments[0])


class Test(BaseCommand):
    def __init__(self, *args, **kwargs):
        super(Test, self).__init__(*args, **kwargs)
        self.response_render_dict['test'] = 'test'

    def execute_command(self):
        io_open(self.request, self.status)
        io_init(self.request, self.status)
        io_start(6, self.request, self.status)


class Status(BaseCommand):
    def __init__(self, *args, **kwargs):
        super(Status, self).__init__(*args, **kwargs)

    def print(self, string):
        _settings = load_settings()
        log_and_print(
            string, logfile=self.logfile, request=self.request, log=_settings['LOGSTATUS'],
            verbose=_settings['PRINTSTATUS']
        )

    def execute_command(self):
        self.print(self.status.get_status_str())
        return self.response()


class Mode(BaseCommand):
    def __init__(self, *args, **kwargs):
        super(Mode, self).__init__(*args, **kwargs)
        self.mode = 'CDS'
        self.available_modes = FRAME_REDUCE_METHODS.keys()

    def execute_command(self):
        self.parse_arguments()
        update_setting('MODE', self.mode)
        self.print('Updated frame reduction mode to {}'.format(self.mode))

    def parse_arguments(self):
        if len(self.arguments) > 0:
            self.mode = str(self.arguments[0]).upper()
            assert self.mode in self.available_modes
        else:
            pass


COMMANDS = {
    'OPEN': Open,
    'INIT': Init,
    # 'SYNC': Sync,
    'START': Start,
    'CLOSE': Close,
    # 'UNLOCK': Unlock,
    # 'CONFIG': Config,
    # 'CONFIGFROMFILE': ConfigFromFile,
    'TEST': Test,
    'STATUS': Status,
    'MODE': Mode
}

skip_updates = {'STATUS'}


def execute_command(interface_command='TEST 0', request=None, status=None):
    split_command = interface_command.split()
    command = split_command[0].upper()
    command = command
    if status is None:
        status = StatusReadWrite()
    log_and_print('received command: {}'.format(interface_command), request=request)
    if command not in skip_updates:
        status.update_current_command(command)
    try:
        arguments = split_command[1:]
    except IndexError:
        arguments = []
    try:
        tcs_command = COMMANDS[command](arguments, interface_command, status=status, request=request)
        command_response = tcs_command.execute_command()
        if command not in skip_updates:
            status.update_command_complete()
        return command_response
    except ConnectionAbortedError:
        if command not in skip_updates:
            status.update_command_complete()
        tb = traceback.format_exc()
        raise ConnectionAbortedError(tb)
    except Exception as e:
        if command not in skip_updates:
            status.update_command_complete()
        tb = traceback.format_exc()
        if not load_settings()['ERRORNAK']:
            error_log_and_print('Received message "{}", but generated error'.format(interface_command))
            error_log_and_print(tb)
            return tb
        else:
            raise ExecutionError(e)


class TCPHandler(socketserver.StreamRequestHandler):
    """
    The request handler class for our server.

    It is instantiated once per connection to the server, and must
    override the handle() method to implement communication to the
    client.
    """

    def print(self, string):
        # try:
        log_and_print(string, request=self.wfile)
        # except ConnectionResetError:
        #     error_log_and_print(traceback.format_exc())
        #     log_and_print(string)

    def handle(self):
        etx = '\u0003'
        nak = '\u0015'
        breaking_handle = 'Breaking handle, {}'.format(self.server.server_address)
        try:
            log_and_print('New connection: {}'.format(self.client_address))
            cont = True
            global stop_threads
            while cont and not stop_threads:
                try:
                    self.data = get_tcp_message(self.rfile, timeout=5)
                    if self.data.upper().startswith('CLOSE'):
                        cont = False
                    return_message = execute_command(self.data, request=self.wfile, status=status)
                    self.print(return_message)
                    self.print(completion_message)
                    self.print(etx)
                except TimeoutError:
                    sleep(1)
                    log_and_print('TIMEOUT')
                except (ExecutionError, EmptyMessage) as e:
                    error_log_and_print("ER [%s]: %r" % (self.client_address[0], e), request=self.wfile)
                    tb = traceback.format_exc()
                    print(tb)
                    error_log_and_print(e, request=self.wfile)
                    if load_settings()['ERRORNAK']:
                        self.print(nak)
                    else:
                        self.print(etx)
                except (ConnectionAbortedError, ConnectionResetError, MemoryError):
                    log_and_print(breaking_handle)
                    cont = False
                    tb = traceback.format_exc()
                    error_log_and_print(tb)
                except CloseHandle:
                    log_and_print(breaking_handle)
                    cont = False
        except Exception as e:
            error_log_and_print("ER [%s]: %r" % (self.client_address[0], e), request=self.wfile)
            tb = traceback.format_exc()
            error_log_and_print(tb, request=self.wfile)
            if load_settings()['ERRORNAK']:
                self.print(nak)
            else:
                self.print(etx)
        print('handle broken')


class StatusServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True


def run_server(server_obj, forever):
    # while True:
    if forever:
        server_obj.serve_forever()
    else:
        server_obj.handle_request()


def server():
    # host, PORT = socket.gethostname(), 9999
    host = load_settings()['HOST']
    port = load_settings()['PORT']
    # host, port = 'localhost', 9999
    # Create the server, binding to localhost on port 9999

    threads = []
    servers = [socketserver.TCPServer((host, port), TCPHandler), StatusServer((host, port+1), TCPHandler)]
    # for p in (port, port+1):
    for _server, p, forever in zip(servers, (port, port+1), (False, True)):
        log_and_print("Starting socket server")
        log_and_print("host: {}".format(host))
        log_and_print("port: {}".format(p))
        _server.allow_reuse_address = True
        servers.append(_server)
        _thread = threading.Thread(target=run_server, args=(_server, forever), daemon=True)
        # Activate the server; this will keep running until you
        # interrupt the program with Ctrl-C
        threads.append(_thread)
        _thread.start()

    cont = True
    # try:
    global stop_threads
    while cont:
        # print("fileno", servers[0].fileno())
        sleep(1)
        for _thread in threads:
            if not _thread.is_alive():
                cont = False
                stop_threads = True
                print('dead thread')
                # raise KeyboardInterrupt

            # _thread.join(timeout=1)
    # except KeyboardInterrupt:
    #     for _server in servers:
    #         _server.shutdown()


def cli_execute_command(interface_command='TEST 0'):
    log_and_print(execute_command(interface_command))
    log_and_print(completion_message)
