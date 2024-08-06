from collections import OrderedDict

from asdetector.utils.files import load_settings

_settings = load_settings()

header_modes = {
    0: 'Stays the same with settings',
    1: 'Stays the same after initialization',
    2: 'Changes with each exposure',
    3: 'Changes with each frame'
}

header_format = OrderedDict()
header_format['NFRAMES'] = {'value': 0, 'comment': 'number of frame in exposure', 'mode': 2}
header_format['FRAME'] = {'value': 0, 'comment': 'current frame number', 'mode': 3}
header_format['EXPTIME'] = {'value': 0, 'comment': '[s] exposure time of all frames including frame 1', 'mode': 2}
header_format['EXPTIMEC'] = {'value': 0, 'comment': '[s] exposure time commanded', 'mode': 2}
header_format['EXPTIMEE'] = {
    'value': 0, 'comment': '[s] effective exposure time given the mode and number of frames', 'mode': 2
}
header_format['FRTIME'] = {
    'value': _settings['FRAMETIMESEC'], 'comment': '[s] approximate time to read one frame', 'mode': 0
}
header_format['TFRAME'] = {
    'value': _settings['FRAMETIMESEC'], 'comment': '[s] time between successive starts of frames', 'mode': 0
}
header_format['NRESETS'] = {'value': 0, 'comment': 'number of reset frames before exposure', 'mode': 2}
header_format['ISRESET'] = {'value': False, 'comment': 'determines if current frame is a reset frame', 'mode': 3}
if _settings['REMOVESCIENCEHEADERS']:
    ncols = _settings['FRAMEX'] - _settings['NUMBEROFSCIENCEHEADERSPERROW']
else:
    ncols = _settings['FRAMEX']
header_format['SIZAXIS1'] = {'value': ncols, 'comment': '', 'mode': 0}
header_format['SIZAXIS2'] = {'value': _settings['FRAMEY'], 'comment': '', 'mode': 0}
header_format['NCOLS'] = {'value': ncols, 'comment': '', 'mode': 0}
header_format['NROWS'] = {'value': _settings['FRAMEY'], 'comment': '', 'mode': 0}
header_format['REDXMODE'] = {
    'value': _settings['MODE'], 'comment': 'reduction mode used to calculate number of frames', 'mode': 2
}
header_format['REFOUT'] = {'value': '', 'comment': 'reference output included in the data', 'mode': 3}  # TODO
header_format['NOUTPUTS'] = {
    'value': _settings['NUMBEROFREADOUTCHANNELS'], 'comment': 'number of detector readout channels', 'mode': 0
}
header_format['AMPMODE'] = {
    'value': '', 'comment': 'Preamplifier mode SE: single-ended mode, DIFF: differential mode', 'mode': 1
}  # TODO
header_format['ASICINDX'] = {'value': 0, 'comment': 'ASIC index number', 'mode': 1}
header_format['ASICADDR'] = {'value': 0, 'comment': 'ASIC address number', 'mode': 1}
header_format['DETECTOR'] = {'value': '', 'comment': 'name of the SCA', 'mode': 1}
header_format['ASICSN'] = {'value': 0, 'comment': 'ASIC serial number', 'mode': 1}
header_format['FPAPOS'] = {'value': 0, 'comment': 'location of sca within the dewar', 'mode': 1}
header_format['MACIESN'] = {'value': 0, 'comment': 'MACIE serial used for interface', 'mode': 1}
header_format['MACIEINT'] = {'value': '', 'comment': 'MACIE interface type', 'mode': 1}
header_format['UTDATE'] = {'value': '', 'comment': 'universal date, YYYY-MM-DD', 'mode': 2}
header_format['UTSTART'] = {'value': '', 'comment': 'universal time at start of exposure, hh:mm:ss.ssssss', 'mode': 2}
header_format['DATE'] = {
    'value': '', 'comment': 'universal datetime when file was created, hh:mm:ss.ssssss', 'mode': 3
}
header_format['DATE-BEG'] = {
    'value': '', 'comment': 'universal datetime at start of exposure, YYYY-MM-DDThh:mm:ss.ssssss', 'mode': 2
}
header_format['DATE-END'] = {
    'value': '', 'comment': 'universal time at end of exposure, YYYY-MM-DDThh:mm:ss.ssssss', 'mode': 3
}
header_format['MJD-BEG'] = {
    'value': '', 'comment': 'modified Julian Date at start of exposure', 'mode': 2
}
header_format['MJD-END'] = {
    'value': '', 'comment': 'modified Julian Date at end of exposure', 'mode': 3
}
header_format['JD-BEG'] = {
    'value': '', 'comment': 'Julian Date at start of exposure', 'mode': 2
}
header_format['JD-END'] = {
    'value': '', 'comment': 'Julian Date at end of exposure', 'mode': 3
}
header_format['EXPSTART'] = {'value': '', 'comment': 'universal time at start of exposure', 'mode': 2}
header_format['EXPEND'] = {'value': '', 'comment': 'modified Julian Date at end of exposure', 'mode': 3}
header_format['EXPMID'] = {'value': '', 'comment': 'modified Julian Date at middle of exposure', 'mode': 3}
header_format['TELAPSE'] = {'value': '', 'comment': '[s] time between start and end of exposure]', 'mode': 3}
header_format['TIMEUNIT'] = {'value': 's', 'comment': 'specifies time unit (always seconds)', 'mode': 0}
header_format['DEINTERL'] = {
    'value': True, 'comment': 'determines whether the frames are deinterlaced or not', 'mode': 1
}
header_format['ASDFNAME'] = {'value': 0, 'comment': 'original filename from asdetector software', 'mode': 3}
header_format['RSTSAVE'] = {'value': False, 'comment': 'determines if reset frames are saved', 'mode': 2}
header_format['RSTTYPE'] = {'value': 'line', 'comment': 'pixel or line reset mode', 'mode': 0}
header_format['LODFIL0'] = {'value': '', 'comment': 'load file used to initialize MACIE-ASIC system', 'mode': 1}
header_format['LODFIL1'] = {'value': '', 'comment': 'load file used to initialize MACIE-ASIC system', 'mode': 1}
header_format['LODFIL2'] = {'value': '', 'comment': 'load file used to initialize MACIE-ASIC system', 'mode': 1}
header_format['LODFIL3'] = {'value': '', 'comment': 'load file used to initialize MACIE-ASIC system', 'mode': 1}
header_format['LODFIL4'] = {'value': '', 'comment': 'load file used to initialize MACIE-ASIC system', 'mode': 1}
header_format['LODFIL5'] = {'value': '', 'comment': 'load file used to initialize MACIE-ASIC system', 'mode': 1}
header_format['LODFIL6'] = {'value': '', 'comment': 'load file used to initialize MACIE-ASIC system', 'mode': 1}
header_format['LODFIL7'] = {'value': '', 'comment': 'load file used to initialize MACIE-ASIC system', 'mode': 1}
header_format['LODFIL8'] = {'value': '', 'comment': 'load file used to initialize MACIE-ASIC system', 'mode': 1}
header_format['LODFIL9'] = {'value': '', 'comment': 'load file used to initialize MACIE-ASIC system', 'mode': 1}
header_format['LODFIL10'] = {'value': '', 'comment': 'load file used to initialize MACIE-ASIC system', 'mode': 1}
header_format['VRESET'] = {'value': 0, 'comment': '[dac] vreset bias applied to detector', 'mode': 1}
header_format['CELLDRAI'] = {'value': 0, 'comment': '[dac] celldrain bias applied to detector', 'mode': 1}
header_format['VBIASGAT'] = {'value': 0, 'comment': '[dac] vbiasgate bias applied to detector', 'mode': 1}
header_format['VBIASPOW'] = {'value': 0, 'comment': '[dac] vbiaspower bias applied to detector', 'mode': 1}
header_format['SUB'] = {'value': 0, 'comment': '[dac] sub bias applied to detector', 'mode': 1}
header_format['DSUB'] = {'value': 0, 'comment': '[dac] dsub bias applied to detector', 'mode': 1}
header_format['DRAIN'] = {'value': 0, 'comment': '[dac] drain bias applied to detector', 'mode': 1}
header_format['VDDA'] = {'value': 0, 'comment': '[dac] vdda bias applied to detector', 'mode': 1}
header_format['VDD'] = {'value': 0, 'comment': '[dac] vdd bias applied to detector', 'mode': 1}
header_format['GND'] = {'value': 0, 'comment': '[dac] digital ground bias applied to detector', 'mode': 1}
header_format['GNDA'] = {'value': 0, 'comment': '[dac] analog ground bias applied to detector', 'mode': 1}
header_format['VREF'] = {'value': 0, 'comment': '[dac] vref bias applied to detector', 'mode': 1}
header_format['CHIP'] = {'value': 0, 'comment': 'detector/asic chip number', 'mode': 1}
header_format['NSCIHEAD'] = {
    'value': _settings['NUMBEROFSCIENCEHEADERSPERROW'], 'comment': 'number science headers per row', 'mode': 0
}
header_format['RMVSCIHD'] = {
    'value': _settings['REMOVESCIENCEHEADERS'], 'comment': 'remove science headers from final image', 'mode': 0
}
for i in range(_settings['NUMBEROFSCIENCEHEADERSPERROW']):
    header_format["SCIWRD{}".format(i+1)] = {'value': 0, 'comment': 'first row science word value', 'mode': 3}
header_format['ABLKLEN'] = {'value': 0, 'comment': 'ASIC generated block length', 'mode': 3}
header_format['ABLKCNT'] = {'value': 0, 'comment': 'ASIC generated block count', 'mode': 3}
header_format['AASICID'] = {'value': 0, 'comment': 'ASIC generated asic ID', 'mode': 3}
header_format['AHDRLEN'] = {'value': 0, 'comment': 'ASIC generated  header length', 'mode': 3}
header_format['ASDPCNT'] = {'value': 0, 'comment': 'ASIC generated science data packet count', 'mode': 3}
header_format['AFF'] = {'value': 0, 'comment': 'ASIC generated full frame[1] or guide window frame[0]', 'mode': 3}
header_format['ARDFRM'] = {'value': 0, 'comment': 'ASIC generated read[1] or reset[0] frame', 'mode': 3}
header_format['AEXPVIDL'] = {'value': 0, 'comment': 'ASIC generated exposure[1] or idle[0]', 'mode': 3}
header_format['ASCIFRM'] = {
    'value': 0, 'comment': 'ASIC generated frame counter within exposure rolls over at 511', 'mode': 3
}
header_format['ASCIXPID'] = {'value': 0, 'comment': 'ASIC generated exposure ID number rolls over at 127', 'mode': 3}

for k, v in _settings['FITSHEADER'].items():
    header_format[k] = v

asic_chip_id_lower_matching = _settings['ASICCHIPIDLOWER']

asic_lookup_table_defaults = _settings['ASICLOOKUPTABLE']

asic_bias_voltage_address_defaults = _settings['ASICBIASVOLTAGEADDRESS']

asic_bias_address_to_fits_header_translation_dict = {
    'VDDA': 'VDDA',
    'VDD': 'VDD',
    'GND': 'GND',
    'GNDA': 'GNDA',
    'SUB': 'SUB',
    'DSUB': 'DSUB',
    'CELLDRAIN': 'CELLDRAI',
    'VRESET': 'VRESET',
    'DRAIN': 'DRAIN',
    'VBIASPOWER': 'VBIASPOW',
    'VBIASGATE': 'VBIASGAT',
    'VREF': 'VREF'
}


def load_asic_bias_voltage_addresses():
    return asic_bias_voltage_address_defaults


# def convert_bias_dac_value_to_mv(dac_value):
#     return dac_value * 4 / (2**12)


# def convert_bias_mv_to_dac_value(millivolts):
#     return int(millivolts * (2**12) / 4)


def load_asic_lookup_table():
    return asic_lookup_table_defaults


def load_asic_bias_voltage_address():
    return asic_bias_voltage_address_defaults
