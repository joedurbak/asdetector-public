base = 'Completed {command_name}'
test = base + ' {test}'
close = base + ' Shutting off power to MACIEs is recommended'
no_cmd = base + ' Not implemented in this system...'

response = {
    'BaseCommand': base,
    'Test': test,
    'Open': base,
    'Init': base,
    'Sync': base,
    'Close': close,
    'Start': base,
    'ConfigFromFile': base,
    'Unlock': no_cmd,
    'Config': base,
    'Status': base,
    'Mode': base
}
