import json
import os
from shutil import copyfile
from datetime import datetime as dt
import re
from threading import Lock

import numpy as np

status_template_file = os.path.join(os.path.dirname(__file__), 'status_template.json')
loadfile_dir = os.path.join(os.path.dirname(__file__), '..', 'detector', 'macie', 'loadfiles')
rel_register_file = 'ACADIA_19p5MHz_mSPIDiv4_SysClkDiv2_LVDS_v1A_multiMACIE-allfiles.mcf'
rel_register_file = os.path.join(loadfile_dir, rel_register_file).replace(os.path.sep, '/')
base_dir = os.path.split(__file__)[0]
base_dir = os.path.split(base_dir)[0]
base_dir = os.path.split(base_dir)[0]

DEFAULT_SETTINGS = {
    'READOUTHARDWARE': 'MACIE',  # Don't change this value unless further development is done for other readout hardware
    'SIMULATION': False,  # Change to True to switch to the simulated API instead of the MACIE API
    'NUMBEROFCAMERAS': 4,  # Number of ASICs (ACADIA, SIDECAR, etc.)
    'NUMBEROFREADOUTCHANNELS': 33,  # Number of readout channels enabled on the ASIC
                                    # including detector and other voltage measurement channels
    'NUMBEROFSCIENCEHEADERSPERROW': 0,  # Number of telemetry header columns at the start of the ASIC readout
    'REMOVESCIENCEHEADERS': True,  # Removes the telemetry header columns discussed above
    'HOST': 'localhost',  # IP address for the TCP server
    'PORT': 9999,  # Port for the TCP server
    'CAMERANAMES': ['C0', 'C1', 'C2', 'C3'],  # Camera names. Can be any string allowed in a filename
    'MODE': 'CDS',  # Ramp data reduction mode
    'MACIEIPLIST': None,  # List of IP addresses to search for the MACIEs.
                          # If None, it will use the built-in API search for the MACIEs
    'FRAMEX': 4224,  # Number of columns expected in the readout
    'FRAMEY': 4096,  # Number of rows expected in the readout
    'MACIEBOPTION': False,  # Boolean value indicating if DMA bit needs to be set (SIDECAR ASIC),
                            #   or the mSPI-specific registers are to be addressed (ACADIA ASIC)
    'MACIEGIGECOMMANDPORT': 0,  # integer indicating the GigE port number (e.g. 42037)
    'MACIEFIRMWARESLOT': True,  # chooses the firmware slot to use on the MACIE (0 or 1)
    'MACIELOADFILES': [],  # list of .mcf, .ald, etc. files should go here
    'REDUCEINTERMEDIATEFRAMES': True,  # Create CDS reduced frames as raw frames are sampled up the ramp
    'REDUCEFINALFRAME': True,  # Create a final reduced frame from the overall data acquisition using method from 'MODE'
    'ASICRESETFRAMES': 1,  # Number of reset frames before acquiring science frames
    'SAVERESETFRAMES': False,  # Choose whether to save reset frames
    'FRAMETIMESEC': 2.863,  # Approximate time for frame readout. Used to calculate number of science frames needed
                            #   based on exposure time and 'MODE'
    'ASICREADFRAMESADDRESS': 0x0000,  # should be changed to match ASIC (ACADIA, SIDECAR, etc.)
    'ASICRESETFRAMESADDRESS': 0x0000,  # should be changed to match ASIC (ACADIA, SIDECAR, etc.)
    'ASICSTARTACQUSITIONADDRESS': 0x0000,  # should be changed to match ASIC (ACADIA, SIDECAR, etc.)
    'ASICSTARTACQUSITIONVALUE': 0x0000,  # should be changed to match ASIC (ACADIA, SIDECAR, etc.)
    'MACIEWAITBETWEENLOADS': 1000,  # time to wait between loading files from 'MACIELOADFILES'
    'MACIESCIENCEREADBLOCKSADDRESS': 0x01b6,  # address used to set MACIE science block size.
                                              #   Used when there are multiple ASICs with interleaved data.
    'INSTRUMENTNAME': 'prime',  # used in the output fits filenames
    'SAVENUMPYARRAY': False,  # save the raw frames as a numpy array without reshaping, deinterlacing, or deinterleaving
                              #   Useful for debugging
    'OUTPUTLOGSTATUSBASEDIR': base_dir,  # base directory used for all outputs: images, logs, status json files
    'DEINTERLACE': True,  # Deinterlace outputs based on number of channels
    'SCIENCEFRAMETIMEOUT': 4000,  # Timeout in ms for reading a frame
    'SCIENCEDATATIMEOUT': 4000,  # Timeout in ms for reading science data from ASIC
    'FITSHEADER': {},  # Dictionary containing all constant headers. Format discussed further in README.md
    'LOGSTATUS': True,  # Choose whether to log outputs from the Status command
                        # (may want to turn off if polled frequently)
    'PRINTSTATUS': True,  # Choose whether to print outputs from the Status command
                          #   (may want to turn off if polled frequently)
    'TCPMSGCLOSE': False,  # Stops messages from being sent over TCP connection when close command is sent.
                           #   Useful to avoid errors if the server client stops listening after a close command.
    'ERRORNAK': True,  # Return NAK instead of ACK when an error occurs
    'AUTORESYNC': False,  # Automatically run INIT command if telemetry data shows ACADIAs are out of sync
    'INITWAIT': 10000,  # Time to wait after INIT for voltages to settle
    'ENABLETESTERRORS': False,  # Sets off errors based on 'TESTERRORS' for testing
    'TESTERRORS': [],  # options: BADOPEN, BADHANDLE, TIMEOUT, BADSTART, BADCLOSE, BADMODE, BADCONFIG
    'ASICLOOKUPTABLE': (  # Table giving the sca number, sca position, and ASIC number for each enabled ASIC
        {'sca': 12345, 'position': 1, 'sce': 123},
        {'sca': 67890, 'position': 2, 'sce': 456},
        {'sca': 23456, 'position': 3, 'sce': 789},
        {'sca': 78901, 'position': 4, 'sce': 234},
    ),
    'ASICCHIPIDLOWER': {
        # ASIC chip id lower from telemetry data used for autoresyncing. depends on telemetry header information.
        #  key is the chip ID, value is the camera number
        0x000: 0,
        0x001: 1,
        0x002: 2,
        0x003: 3,
    },
    'ASICIDLOWERTELEMETRYROW': 0,  # row containing the asic id lower telemetry information
    'ASICIDLOWERTELEMETRYCOLUMN': 0,  # column containing the asic id lower telemetry information
    'ASICBIASVOLTAGEADDRESS': {  # ASIC address to read the detector voltage. Skips value if set to None
        'VDDA': None,
        'VDD': None,
        'GND': None,
        'GNDA': None,
        'SUB': None,
        'DSUB': None,
        'CELLDRAIN': None,
        'VRESET': None,
        'DRAIN': None,
        'VBIASPOWER': None,
        'VBIASGATE': None,
        'VREF': None
    }
}


class JSONHandler:
    def __init__(self, json_file):
        self.lock = Lock()
        self.json_file = json_file

    def json_dict_from_file(self):
        self.lock.acquire()
        with open(self.json_file, 'r') as f:
            json_dict = json.load(f)
        self.lock.release()
        return json_dict

    def save_dict_to_json(self, dictionary):
        self.lock.acquire()
        json_string = json.dumps(dictionary, indent=2)
        dirname = os.path.dirname(self.json_file)
        if not os.path.isdir(dirname):
            os.makedirs(dirname)

        with open(self.json_file, 'w') as f:
            f.write(json_string)
        self.lock.release()


def json_dict_from_file(json_file):
    return JSONHandler(json_file).json_dict_from_file()


def save_dict_to_json(dictionary, file_name):
    JSONHandler(file_name).save_dict_to_json(dictionary)


def gen_settings_file_name():
    return os.path.join(base_dir, 'settings.json')


def load_settings():
    try:
        input_settings_dict = json_dict_from_file(gen_settings_file_name())
    except FileNotFoundError as e:
        print(e)
        save_settings(DEFAULT_SETTINGS)
        input_settings_dict = {}
    settings_dict = input_settings_dict.copy()
    for k, v in input_settings_dict.items():
        settings_dict[k.upper()] = v
    for k, v in DEFAULT_SETTINGS.items():
        input_settings_dict[k] = settings_dict.get(k, v)
    # print(input_settings_dict)
    return input_settings_dict


def save_settings(settings_dict):
    fname = gen_settings_file_name()
    save_dict_to_json(settings_dict, fname)


def update_setting(key, value):
    settings = load_settings()
    settings[key.upper()] = value
    save_settings(settings)


def get_next_iteration(directory):
    files = os.listdir(directory)
    iterations = [re.findall('\d+', f) for f in files]
    iterations = [int(i[1]) for i in iterations if i != []]
    try:
        iteration = max(iterations) + 1
    except ValueError:
        iteration = 0
    return iteration


def gen_file_name(prefix=None, stamp_type='day', suffix=''):
    if prefix is None:
        prefix = ''
    else:
        prefix = '{}_'.format(prefix)
    _base_dir = load_settings()['OUTPUTLOGSTATUSBASEDIR']
    datetime = dt.utcnow()
    if stamp_type == 'day':
        file_name = '{}{:04d}{:02d}{:02d}'.format(prefix, datetime.year, datetime.month, datetime.day)
    elif stamp_type == 'iso':
        file_name = dt.isoformat(dt.now()).replace(':', '_')
    else:
        file_name = 'out'
    file_name = file_name + suffix
    return _base_dir, file_name


def gen_logfile_name(prefix=None):
    _base_dir, log_name = gen_file_name(prefix)
    logfile = os.path.join(_base_dir, 'logs', log_name)
    return logfile


def gen_status_file_name(prefix=None):
    _base_dir, file_name = gen_file_name(prefix)
    status_file = os.path.join(_base_dir, 'status', 'status.json')
    return status_file


def status_dict_from_file(json_file=gen_status_file_name()):
    return JSONHandler(json_file).json_dict_from_file()


def status_dict_to_json(dictionary, file_name=gen_status_file_name()):
    JSONHandler(file_name).save_dict_to_json(dictionary)


def gen_status_copy_file_name(status_file, prefix=None):
    _dict = json_dict_from_file(status_file)
    _time = _dict['CommandStartTime'].replace(':', '_')
    _cmd = _dict['CurrentCommand']
    _base_dir, file_name = gen_file_name(prefix, stamp_type='iso')
    if prefix is None:
        prefix = ''
    else:
        prefix = '{}_'.format(prefix)
    return os.path.join(_base_dir, 'status', '{}{}_{}.json'.format(prefix, _time, _cmd))


def gen_logfile(logfile):
    if not os.path.isfile(logfile):
        logfile_dir = os.path.split(logfile)[0]
        if not os.path.isdir(logfile_dir):
            os.makedirs(logfile_dir)
        with open(logfile, 'w') as f:
            pass


def gen_status_file(status_file=gen_status_file_name()):
    if not os.path.isfile(status_file):
        logfile_dir = os.path.split(status_file)[0]
        if not os.path.isdir(logfile_dir):
            os.makedirs(logfile_dir)
        copyfile(status_template_file, status_file)
    else:
        copy_file_name = gen_status_copy_file_name(status_file)
        copyfile(status_file, copy_file_name)
        copyfile(status_template_file, status_file)


def gen_detector_file_name(prefix=None):
    file_format = '{0:04d}.'
    _base_dir, date_dir = gen_file_name()
    if prefix is not None:
        file_format = '{}.{}.{}'.format(date_dir, prefix, file_format)
    # _base_dir, date_dir = gen_file_name()
    output_dir = os.path.join(_base_dir, 'output')
    raw_dir = os.path.join(output_dir, 'raw', date_dir)
    res_dir = os.path.join(output_dir, 'res', date_dir)
    reduced_dir = os.path.join(output_dir, 'reduced', date_dir)

    for d in [reduced_dir, res_dir, raw_dir]:
        if not os.path.isdir(d):
            os.makedirs(d)

    iteration = get_next_iteration(raw_dir)
    file_prefix = file_format.format(iteration)
    file_prefix = file_prefix + '{cam}'
    # raw_dir = os.path.join(raw_dir, file_prefix)
    # res_dir = os.path.join(res_dir, file_prefix)
    frame_file_format = file_prefix + '.{frame:04d}.fits'
    reset_file_format = 'reset.' + frame_file_format
    reduced_file_format = os.path.join(reduced_dir, file_prefix+'.fits')
    raw_frame_file_format = os.path.join(raw_dir, frame_file_format)
    reset_frame_file_format = os.path.join(raw_dir, reset_file_format)
    res_frame_file_format = os.path.join(res_dir, frame_file_format)
    return file_prefix, reduced_dir, raw_dir, res_dir, reduced_file_format, raw_frame_file_format,\
        res_frame_file_format, reset_frame_file_format


def gen_offsets_file_name():
    basedir, date = gen_file_name()
    return os.path.join(basedir, 'offsets', 'offsets.dat')


def save_offsets(offsets, offset_file_name=gen_offsets_file_name()):
    offsets_array = np.asarray(offsets).transpose()
    offsets_path, file_name = os.path.split(offset_file_name)
    if not os.path.isdir(offsets_path):
        os.makedirs(offsets_path)
    if os.path.isfile(offset_file_name):
        _base_dir, copy_file_name = gen_file_name(prefix='offsets', stamp_type='iso', suffix='.dat')
        copyfile(offset_file_name, os.path.join(offsets_path, copy_file_name))
    np.savetxt(offset_file_name, offsets_array, fmt='%2x')


def load_offsets(offset_file_name=gen_offsets_file_name()):
    offset_array = np.loadtxt(
        offset_file_name, converters={_: lambda s: int(s, 16) for _ in range(load_settings()['NUMBEROFCAMERAS'])}
    )
    return offset_array.astype(np.int16).transpose().tolist()
