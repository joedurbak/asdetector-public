from asdetector.utils.files import load_settings
from asdetector.detector.macie.io import io_open, io_init, io_start, io_close, io_config, io_sync

# hardware = load_settings()['READOUTHARDWARE']

# if hardware.upper() == 'MACIE':
#     from asdetector.detector.macie.io import io_open, io_init, io_start, io_close, io_config, io_sync

# elif hardware.upper() == 'LEACH':
#     from asdetector.detector.leach.io import io_open, io_init, io_start, io_close, io_config, io_sync

# elif hardware.upper() == 'SIMULATOR':
#     from asdetector.detector.simulator.io import io_open, io_init, io_start, io_close, io_config, io_sync

# else:
#     raise ValueError("{} is an invalid option for readout hardware".format(hardware))
