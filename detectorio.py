import argparse

from asdetector.interface import cli_execute_command, COMMANDS, server


parser = argparse.ArgumentParser()

available_commands = ", ".join(COMMANDS.keys())
available_commands = '{}, {}'.format(available_commands, 'SERVER')

parser.add_argument('COMMAND', type=str, nargs='+', help='available commands: {}'.format(available_commands))

args = parser.parse_args()

_command = args.COMMAND

if _command[0].upper() == 'SERVER':
    server()
else:
    cli_execute_command(' '.join(_command))

