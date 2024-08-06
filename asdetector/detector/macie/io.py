import os
import ctypes as ct
import time
import threading
import traceback
from datetime import datetime as dt


import numpy as np
from astropy.io import fits
from pandas import Timestamp

from asdetector.detector.macie import header
from asdetector.utils.logging import log_and_print, error_log_and_print
from asdetector.utils.files import save_dict_to_json, json_dict_from_file, gen_detector_file_name, load_settings
from asdetector.utils.image import ArrayImage, reduce_image_from_array, intermediate_reduce_image_from_array, \
    calc_num_frames, calc_effective_exposure_time, gen_fits_header, ImageHandler, ssr_calc_frames
from asdetector.utils.status import Status

if load_settings()['SIMULATION']:
    from asdetector.detector.macie import apisimulator as api
else:
    from asdetector.detector.macie import api


macie_save_file_format = 'macie_interface.sn.conn.asic.{sn}.{conn}.{asic}.json'
macie_save_interfaces_dir = os.path.join(os.path.dirname(api.__file__), 'saved_macie_interfaces')


class MissingMACIEError(Exception):
    pass


def composite_byte_to_byte_list(integer):
    bin_string = bin(integer)[2:][::-1]
    return [2**power for power, bit in enumerate(bin_string) if int(bit)]


def byte_list_to_composite_byte(byte_list):
    integer = 0
    for byte in byte_list:
        integer += byte
    return integer


def byte_list_to_index_list(byte_list):
    return [int(np.log2(i)) for i in byte_list]


def mcf_abs_from_rel(input_mcf, output_mcf):
    with open(input_mcf, 'r') as f:
        input_lines = f.readlines()
    output_lines = []
    for line in input_lines:
        if line.upper().startswith('LOAD'):
            split_line = line.split()
            load = split_line[0]
            f_path = split_line[1]
            f_abs_path = os.path.join(os.path.dirname(input_mcf), f_path).replace(os.path.sep, '/')
            new_line = ' '.join((load, f_abs_path))
            output_lines.append(new_line)
        else:
            output_lines.append(line)
    with open(output_mcf, 'w') as f:
        f.write(''.join(output_lines))


def datetime_to_julian_date(datetime):
    ts = Timestamp(datetime)
    jd = ts.to_julian_date()
    return jd


def julian_date_to_modified_julian_date(julian_date):
    return julian_date - 2400000.5


def datetime_to_modified_julian_date(datetime):
    jd = datetime_to_julian_date(datetime)
    return julian_date_to_modified_julian_date(jd)


class BaseMACIE:
    def __init__(
            self, card=None, frame_x=4224, frame_y=4096, b_option=True, b_24_bit=0, n_science_headers=0,
            remove_science_headers=True
    ):
        """

        Parameters
        ----------
        card : api.CardInfo
        """
        self.settings = load_settings()
        self.handle = 0
        self.asic_type = 0
        self.all_macies = 0
        self.all_asics = 0
        self.list_macies = []
        self.list_asics = []
        self.list_macies_index = []
        self.list_asics_index = []
        self.card = card
        self.connection = api.Connection.NONE
        self.b_option = b_option
        self.b_24_bit = b_24_bit
        self.mode = 0
        self.timeout = 1000
        self.science_frame_timeout = self.settings['SCIENCEFRAMETIMEOUT']
        self.science_data_timeout = self.settings['SCIENCEDATATIMEOUT']
        self.frame_x = frame_x
        self.frame_y = frame_y
        self.frame_size = self.frame_x * self.frame_y
        self.dcf_file = ''
        self.reset_frames = self.settings['ASICRESETFRAMES']
        self.request = None
        self.logfile = None
        self.save_dict = {}
        self.save_name = ''
        self.science_read_block_size = self.frame_x
        self.blocks_per_frame = int(self.frame_size / self.science_read_block_size)
        self.total_frame_size = self.frame_size
        # self.science_frames = {}
        # self.science_headers = {}
        self.deinterleaving_array = np.asarray([np.arange(self.frame_size)])
        self.cam_names = []
        self.prefix = '{cam}'
        self.reduced_dir = '{cam}'
        self.res_dir = '{cam}'
        self.raw_dir = '{cam}'
        self.reduced_file_format = '{cam}'
        self.res_frame_file_format = '{cam}.{frame:04d}'
        self.reset_frame_file_format = '{cam}.{frame:04d}'
        self.raw_frame_file_format = '{cam}.{frame:04d}'
        self.header = header.header_format
        self.header_keys_ordered = header.header_format.keys()
        self.asic_info_header = {}
        self.status = Status()
        self.n_usb_science_buffers = 4
        self.exposure_start_time = dt.utcnow()
        self.image_handler = ImageHandler()
        self.n_science_headers = n_science_headers
        self.remove_science_headers = remove_science_headers
        self.sync_file = ''
        self.fits_headers = {}
        self.image_arrays = {}
        self.ramps = {}
        self.resync = False

    def gen_save_dict(self):
        card_dict = api.card_to_dict(self.card)
        self.save_dict = {
            'handle': self.handle,
            'asic_type': self.asic_type,
            'all_macies': self.all_macies,
            'all_asics': self.all_asics,
            'list_macies': self.list_macies,
            'list_asics': self.list_asics,
            'list_macies_index': self.list_macies_index,
            'list_asics_index': self.list_asics_index,
            'card': card_dict,
            'connection': int(self.connection),
            'b_option': self.b_option,
            'b_24_bit': self.b_24_bit,
            'mode': self.mode,
            'timeout': self.timeout,
            'science_frame_timeout': self.science_frame_timeout,
            'science_data_timeout': self.science_data_timeout,
            'frame_x': self.frame_x,
            'frame_y': self.frame_y,
            'frame_size': self.frame_size,
            'dcf_file': self.dcf_file,
            'reset_frames': self.reset_frames,
            'logfile': self.logfile,
            'save_name': self.save_name,
            'science_read_block_size': self.science_read_block_size,
            'blocks_per_frame': self.blocks_per_frame,
            'total_frame_size': self.total_frame_size,
            'cam_names': self.cam_names,
            'settings': self.settings,
            'header': self.header,
            'asic_info_header': self.asic_info_header,
            'n_usb_science_buffers': self.n_usb_science_buffers,
            'n_science_headers': self.n_science_headers,
            'remove_science_headers': self.remove_science_headers,
            'sync_file': self.sync_file
        }

    def gen_save_name(self):
        save_dir = macie_save_interfaces_dir
        if not os.path.isdir(save_dir):
            os.makedirs(save_dir)
        self.save_name = os.path.join(save_dir, macie_save_file_format.format(
            sn=self.card.macie_serial_number, conn=int(self.connection), asic=hex(self.asic_type)
        ))
        print(self.save_name)
        return self.save_name

    def save(self):
        self.gen_save_name()
        self.gen_save_dict()
        self.print('saving macie interface object to {}'.format(self.save_name))
        # self.print(self.save_dict)
        save_dict_to_json(self.save_dict, self.save_name)
        self.save_asic_data_frame_deinterleaving_array()
        return self.save_name

    def load(self, save_dict_file_name, request=None, status=None):
        if status is None:
            self.status = Status()
        self.request = request
        self.save_dict = json_dict_from_file(save_dict_file_name)
        card_dict = self.save_dict['card']
        card_dict['ip_address'] = (ct.c_ubyte*4)(*card_dict['ip_address'])
        for k, v in card_dict.items():
            if isinstance(v, str):
                card_dict[k] = v.encode('utf-8')
        self.handle = self.save_dict['handle']
        self.asic_type = self.save_dict['asic_type']
        self.all_macies = self.save_dict['all_macies']
        self.all_asics = self.save_dict['all_asics']
        self.list_macies = self.save_dict['list_macies']
        self.list_asics = self.save_dict['list_asics']
        self.list_macies_index = self.save_dict['list_macies_index']
        self.list_asics_index = self.save_dict['list_asics_index']
        self.card = api.CardInfo(**self.save_dict['card'])
        self.connection = self.save_dict['connection']
        self.b_option = self.save_dict['b_option']
        self.b_24_bit = self.save_dict['b_24_bit']
        self.mode = self.save_dict['mode']
        self.timeout = self.save_dict['timeout']
        self.science_frame_timeout = self.save_dict['science_frame_timeout']
        self.science_data_timeout = self.save_dict['science_data_timeout']
        self.frame_x = self.save_dict['frame_x']
        self.frame_y = self.save_dict['frame_y']
        self.frame_size = self.save_dict['frame_size']
        self.dcf_file = self.save_dict['dcf_file']
        self.reset_frames = self.save_dict['reset_frames']
        self.logfile = self.save_dict['logfile']
        self.save_name = self.save_dict['save_name']
        self.science_read_block_size = self.save_dict['science_read_block_size']
        self.blocks_per_frame = self.save_dict['blocks_per_frame']
        self.total_frame_size = self.save_dict['total_frame_size']
        self.cam_names = self.save_dict['cam_names']
        self.settings = self.save_dict['settings']
        self.header = self.save_dict['header']
        self.asic_info_header = self.save_dict['asic_info_header']
        self.n_usb_science_buffers = self.save_dict['n_usb_science_buffers']
        self.n_science_headers = self.save_dict['n_science_headers']
        self.remove_science_headers = self.save_dict['remove_science_headers']
        self.sync_file = self.save_dict['sync_file']
        self.gen_save_dict()
        self.load_asic_data_frame_deinterleaving_array()
        api.free()
        api.init()
        api.check_interfaces(self.settings['MACIEGIGECOMMANDPORT'], self.settings['MACIEIPLIST'])
        self.get_handle()

        self.print('loaded file {} with class {}'.format(save_dict_file_name, self.__class__.__name__))

    def print(self, string):
        log_and_print(string, logfile=self.logfile, request=self.request)

    def download_file(self, load_file):
        if load_file.endswith('.mcf') or load_file.endswith('.glf') or load_file.endswith('.ald'):
            self.download_load_file(load_file)
        elif load_file.endswith('.mrf'):
            self.download_macie_file(load_file)
        elif load_file.endswith('.mcd'):
            self.download_asic_file(load_file)

    def open(self, request=None, status=None):
        if status is None:
            status = Status()
        self.status = status
        self.request = request
        self.get_handle()
        self.get_available_macies()

    def sync(self, request=None, status=None):
        if status is None:
            status = Status()
        self.status = status
        _settings = load_settings()
        self.request = request
        load_file = self.sync_file.replace(os.path.sep, '/')
        self.print('Loading: {}'.format(load_file))
        self.download_file(load_file)

    def init(self, firmware_slot=True, load_files=tuple(), request=None, status=None):
        if status is None:
            status = Status()
        self.status = status
        _settings = load_settings()
        self.request = request
        self.load_macie_firmware(firmware_slot, self.all_macies)
        for load_file in load_files:
            if self.all_macies == 0:
                self.get_available_macies()
            if self.all_asics == 0:
                self.get_available_asics()
            self.print('Loading: {}'.format(load_file))
            self.download_file(load_file)
            time.sleep(_settings['MACIEWAITBETWEENLOADS']/1000)
        if self.all_macies == 0:
            self.get_available_macies()
        if self.all_asics == 0:
            self.get_available_asics()
        self.write_macie_register(_settings['MACIESCIENCEREADBLOCKSADDRESS'], self.science_read_block_size - 1)
        self.blocks_per_frame = int(self.frame_size / self.science_read_block_size)
        self.total_frame_size = self.frame_size * len(self.list_asics_index)
        self.gen_asic_data_frame_deinterleaving_array()
        self.gen_cam_names()
        for asic in self.list_asics_index:
            self.asic_info_header[str(asic)] = {}
        self.gen_init_header_values(load_files)

    def close(self, request=None, status=None):
        if status is None:
            status = Status()
        self.status = status
        self.request = request
        # self.close_science_interface()

    def capture_frame(self, frame_number, reset=False, skip_frame=False, save_science_frame=True):
        all_data = self.read_science_frame()
        self.gen_end_time_headers()
        self.header['FRAME']['value'] = frame_number
        if self.settings['SAVENUMPYARRAY']:
            np.save(
                self.reduced_file_format.format(cam='{:04d}'.format(frame_number)).replace('.fits', '.npy'), all_data
            )
        self.print('acquired data frame {} with shape {}'.format(frame_number, all_data.shape))
        thread = threading.Thread(
            target=self.handle_frames, args=(all_data, frame_number, reset, skip_frame, save_science_frame),
            name=self.prefix.format(cam='')
        )
        thread.start()
        return thread

    def save_frame(self, image_array, filename, fits_header=None):
        if fits_header is None:
            fits_header_dict = self.header.copy()
            fits_header = gen_fits_header(fits_header_dict)
        # fits_header = fits_header.copy()
        # fits_header['DATE']['value'] = dt.isoformat(dt.utcnow())
        # fits_header['ASDFNAME']['value'] = os.path.basename(filename)
        fits_header['DATE'] = dt.isoformat(dt.utcnow())
        fits_header['ASDFNAME'] = os.path.basename(filename)
        if self.remove_science_headers:
            image_array = image_array[:, self.n_science_headers:]
        self.image_handler.save_image(image_array, filename, fits_header)

    def gen_asic_data_frame_deinterleaving_array_fname(self):
        return os.path.join(os.path.dirname(self.gen_save_name()), 'asic_data_deinterleaving_array.npy')

    def gen_asic_data_frame_deinterleaving_array(self):
        n_asics = len(self.list_asics)
        total_data_blocks = self.blocks_per_frame * n_asics
        all_indices = np.arange(self.total_frame_size).reshape(total_data_blocks, self.science_read_block_size)
        index_matcher = np.arange(total_data_blocks) % n_asics
        self.deinterleaving_array = np.asarray(
            [all_indices[index_matcher == i].reshape(self.frame_size) for i in range(n_asics)]
        )
        if self.settings['DEINTERLACE']:
            deinterleaving_array = []
            reshaped_arrays = [arr.reshape(self.frame_y, self.frame_x) for arr in self.deinterleaving_array]
            for arr in reshaped_arrays:
                array_img = ArrayImage(arr)
                array_img.deinterlace()
                deinterleaving_array.append(array_img.image.reshape(self.frame_size))

            self.deinterleaving_array = np.asarray(deinterleaving_array, dtype=np.int32)

    # def header_and_data

    def save_asic_data_frame_deinterleaving_array(self):
        np.save(self.gen_asic_data_frame_deinterleaving_array_fname(), self.deinterleaving_array)

    def gen_cam_names(self):
        self.cam_names = [self.settings['CAMERANAMES'][index] for index in self.list_asics_index]

    def load_asic_data_frame_deinterleaving_array(self):
        try:
            self.deinterleaving_array = np.load(self.gen_asic_data_frame_deinterleaving_array_fname())

        except FileNotFoundError:
            print('File not found, {}'.format(self.gen_asic_data_frame_deinterleaving_array_fname()))
            try:
                self.gen_asic_data_frame_deinterleaving_array()
            except ValueError:
                pass

    def deinterleave(self, all_data_array):
        return [all_data_array[indices].reshape(self.frame_y, self.frame_x) for indices in self.deinterleaving_array]

    def parse_science_header(self, frame, cam_name, cam_index):
        science_header = {}
        return science_header, cam_name, cam_index

    def format_frame_info(self, frame, frame_number, cam_name, cam_index, fits_header, reset=False):
        science_header, cam_name, cam_index = self.parse_science_header(frame, cam_name, cam_index)
        if reset:
            f_name_format = self.reset_frame_file_format
            fits_header['ISRESET']['value'] = True
        else:
            f_name_format = self.raw_frame_file_format
            fits_header['ISRESET']['value'] = False
        for k, v in self.asic_info_header[str(cam_index)].items():
            fits_header[k]['value'] = v
        for k, v in science_header.items():
            fits_header[k]['value'] = v
        f_name = f_name_format.format(cam=cam_name, frame=frame_number)
        fits_header = gen_fits_header(fits_header)
        return f_name, cam_name, cam_index, fits_header

    def handle_frames(self, all_data_array, frame_number, reset=False, skip_frame=False, save_science_frame=True):
        asic_frames = self.deinterleave(all_data_array)
        if (not reset or self.settings['SAVERESETFRAMES']) and not skip_frame and save_science_frame:
            threads = []
            for frame, cam_name, cam_index in zip(asic_frames, self.cam_names, self.list_asics_index):
                _header = self.header.copy()
                f_name, _cam_name, _cam_index, _header = self.format_frame_info(
                    frame, frame_number, cam_name, cam_index, _header, reset
                )
                self.fits_headers[f_name] = _header
                self.image_arrays[f_name] = frame
                # raw_frame_list.append((frame, f_name, _header))
                # self.save_frame(frame, f_name, _header)

                thread = threading.Thread(
                    target=self.handle_frame, name=_cam_name+str(frame_number)+str(reset),
                    args=(f_name, frame, _cam_name, _cam_index, frame_number, _header, reset)
                )
                thread.start()
                threads.append(thread)
            for thread in threads:
                thread.join(timeout=self.settings['FRAMETIMESEC']*5)
                if thread.is_alive():
                    raise TimeoutError('{} thread is taking too long, moving on'.format(thread.name))

    def handle_frame(self, raw_fname, frame, cam_name, cam_index, frame_number, fits_header, reset=False):
        # self.save_frame(frame, raw_fname, fits_header)
        self.save_frame(self.image_arrays[raw_fname], raw_fname, self.fits_headers[raw_fname])
        if not reset:
            self.status.update_exposure_frames(raw_fname, cam_index)
            # self.science_frames[cam_name].append(frame)
            # self.science_headers[cam_name].append(fits_header)
            self.ramps[cam_name].append(raw_fname)
        if self.settings['REDUCEINTERMEDIATEFRAMES'] and not reset:
            # reduced_image = intermediate_reduce_image_from_array(np.asarray(self.science_frames[cam_name]))
            reduction_frames = np.asarray([self.image_arrays[raw_name] for raw_name in self.ramps[cam_name]])
            reduced_image = intermediate_reduce_image_from_array(reduction_frames)
            f_name = self.res_frame_file_format.format(cam=cam_name, frame=frame_number)
            self.save_frame(reduced_image, f_name, self.fits_headers[raw_fname])
            self.status.update_intermediate_reduced_frame_frames(f_name, cam_index)

    def reduce_frames(self):
        if self.settings['REDUCEFINALFRAME']:
            for cam_name, raw_names in self.ramps.items():
                image_arrays = np.asarray([self.image_arrays[raw_name] for raw_name in raw_names])
                threading.Thread(target=self.reduce_frame, args=(cam_name, np.asarray(image_arrays))).start()
            # for cam_name, image_arrays in self.science_frames.items():
            #     threading.Thread(target=self.reduce_frame, args=(cam_name, np.asarray(image_arrays))).start()

    def reduce_frame(self, cam_name, array):
        img = reduce_image_from_array(array)
        f_name = self.reduced_file_format.format(cam=cam_name)
        raw_name = self.ramps[cam_name][-1]
        # _header = self.science_headers[cam_name][-1]  # TODO: incorporate times from each of the frames into header
        _header = self.fits_headers[raw_name]
        self.save_frame(img, f_name, _header)
        self.status.update_final_reduced_exposure(f_name, self.cam_names.index(cam_name))

    def start_asic_acquisition(self, data_frames):
        pass

    def start(self, exposure_time, skip_time=0, request=None, status=None, save_science_frame=True):
        self.settings = load_settings()
        science_frames = calc_num_frames(exposure_time)
        skip_frames = ssr_calc_frames(skip_time, self.settings['FRAMETIMESEC'])
        self.print('Skipping {} frames per saved frame'.format(skip_frames))
        if not save_science_frame:
            self.print('Not saving frames')
        skips = []
        remaining_frames = science_frames
        while remaining_frames > 0:
            skips.append(False)
            remaining_frames -= 1
            for i in range(skip_frames):
                skips.append(True)
                remaining_frames -= 1
        skips = skips[:science_frames]
        if status is None:
            status = Status()
        self.status = status
        self.request = request
        self.configure_science_interface()
        self.prefix, self.reduced_dir, self.raw_dir, self.res_dir, self.reduced_file_format, \
            self.raw_frame_file_format, self.res_frame_file_format, self.reset_frame_file_format = \
            gen_detector_file_name(self.settings['INSTRUMENTNAME'])
        self.header['NFRAMES']['value'] = science_frames
        self.header['EXPTIME']['value'] = science_frames * self.settings['FRAMETIMESEC']
        self.header['EXPTIMEC']['value'] = exposure_time
        self.header['EXPTIMEE']['value'] = calc_effective_exposure_time(science_frames)
        self.header['REDXMODE']['value'] = self.settings['MODE']
        self.header['NRESETS']['value'] = self.reset_frames
        self.header['RSTSAVE']['value'] = self.settings['SAVERESETFRAMES']
        for cam_name in self.cam_names:
            # self.science_frames[cam_name] = []
            # self.science_headers[cam_name] = []
            self.ramps[cam_name] = []
        self.status.update_total_frame_count(science_frames)
        macie_registers_to_check = []
        for register in macie_registers_to_check:
            for m in self.list_macies:
                val = self.read_macie_register(register, select_macies=m)
                self.print("macie: {}\tregister: {}\tvalue: {}".format(m, hex(register), hex(val)))
        total_frames = self.reset_frames + science_frames
        self.gen_start_time_headers()
        self.start_asic_acquisition(science_frames)
        self.status.update_exposure_time_remaining(total_frames * self.settings['FRAMETIMESEC'])
        # try:
        for frame in range(self.reset_frames):
            self.capture_frame(frame, True, save_science_frame=save_science_frame)
            total_frames -= 1
            time_remaining = total_frames * self.settings['FRAMETIMESEC']
            self.status.update_exposure_time_remaining(time_remaining)
            self.print('Reset {} complete, acquisition time remaining {}'.format(frame, time_remaining))
        self.gen_start_time_headers()
        threads = []
        for frame, skip_frame in enumerate(skips):
            threads.append(self.capture_frame(frame, skip_frame=skip_frame, save_science_frame=save_science_frame))
            total_frames -= 1
            time_remaining = total_frames * self.settings['FRAMETIMESEC']
            self.status.update_exposure_time_remaining(time_remaining)
            self.print('Science frame {} complete, acquisition time remaining {}'.format(frame, time_remaining))
        postprocess_overhead_start = dt.now()
        for thread in threads:
            thread.join(timeout=self.settings['FRAMETIMESEC']*5)
            if thread.is_alive():
                raise TimeoutError('{} thread is taking too long, moving on'.format(thread.name))
        postprocess_overhead_time = (dt.now()-postprocess_overhead_start).total_seconds()
        self.print('Total postprocessing overhead time: {}'.format(postprocess_overhead_time))
        if save_science_frame:
            threading.Thread(target=self.reduce_frames).start()
        # save_dict_to_json(
        #     self.science_headers, os.path.join(os.path.dirname(self.save_name), 'science_headers.json')
        # )
        # except api.ImageAcquisitionError:
        #     tb = traceback.format_exc()
        #     error_log_and_print(tb, request=self.request)
        self.close_science_interface()
        api.free()

    def gen_init_header_values(self, load_files):
        self.gen_amp_mode()
        self.gen_asic_info_headers()
        self.header['MACIESN']['value'] = self.card.macie_serial_number
        self.header['MACIEINT']['value'] = str(self.connection)
        self.header['DEINTERL']['value'] = self.settings['DEINTERLACE']
        for i, load_file in enumerate(load_files):
            self.header['LODFIL{}'.format(i)]['value'] = os.path.basename(load_file)
        self.gen_bias_headers()

    def gen_amp_mode(self):
        self.header['AMPMODE']['value'] = ''  # TODO: figure out how to determine this

    def gen_asic_info_headers(self):
        table_info = header.load_asic_lookup_table()
        for address, index in zip(self.list_asics, self.list_asics_index):
            str_index = str(index)
            self.asic_info_header[str_index]['ASICINDX'] = index
            self.asic_info_header[str_index]['ASICADDR'] = address
            self.asic_info_header[str_index]['DETECTOR'] = table_info[index]['sca']
            self.asic_info_header[str_index]['ASICSN'] = table_info[index]['sce']
            self.asic_info_header[str_index]['FPAPOS'] = table_info[index]['position']
            self.asic_info_header[str_index]['CHIP'] = table_info[index]['position']

    def gen_bias_headers(self):
        bias_addresses = header.load_asic_bias_voltage_addresses()
        for bias, header_name in header.asic_bias_address_to_fits_header_translation_dict.items():
            bias_address = bias_addresses[bias]
            if bias_address is not None:
                value = self.read_asic_register(bias_address)
            else:
                value = 0
            self.header[header_name]['value'] = value

    def gen_start_time_headers(self):
        utc_dt = dt.utcnow()
        self.exposure_start_time = utc_dt
        utc_dt_iso = utc_dt.isoformat()
        self.header['UTDATE']['value'] = utc_dt_iso[0:10]
        self.header['UTSTART']['value'] = utc_dt_iso[11:]
        self.header['DATE-BEG']['value'] = utc_dt_iso
        jd = datetime_to_julian_date(utc_dt)
        mjd = julian_date_to_modified_julian_date(jd)
        self.header['MJD-BEG']['value'] = mjd
        self.header['JD-BEG']['value'] = jd
        self.header['EXPSTART']['value'] = mjd

    def gen_end_time_headers(self):
        utc_dt = dt.utcnow()
        utc_dt_iso = utc_dt.isoformat()
        self.header['DATE-END']['value'] = utc_dt_iso
        jd = datetime_to_julian_date(utc_dt)
        mjd = julian_date_to_modified_julian_date(jd)
        mid_mjd = np.mean((mjd, self.header['EXPSTART']['value']))
        self.header['EXPEND']['value'] = mjd
        self.header['EXPMID']['value'] = mid_mjd
        self.header['MJD-END']['value'] = mjd
        self.header['JD-END']['value'] = jd
        self.header['TELAPSE']['value'] = (utc_dt - self.exposure_start_time).total_seconds()

    def gen_fits_header(self, header_dict=None):
        if header_dict is None:
            header_dict = self.header
        return gen_fits_header(header_dict)

    def read_asic_serial_number(self, select_asics=None):
        select_asics = self._get_read_select_asics(select_asics)
        return 0  # TODO: figure out how to read serial number

    def generate_configure_mode(self):
        pass

    def configure_science_interface(self):
        pass

    def read_science_frame(self):
        return np.ones((self.science_read_block_size,))

    def read_science_data(self, n_science_words_read):
        pass

    def close_science_interface(self, select_macies=None):
        pass

    def _set_write_select_macies(self, select_macies):
        if select_macies is None:
            return self.all_macies
        return select_macies

    def _get_read_select_macies(self, select_macies):
        if select_macies is None:
            return self.list_macies[0]
        return select_macies

    def _set_write_select_asics(self, select_asics):
        if select_asics is None:
            return self.all_asics
        return select_asics

    def _get_read_select_asics(self, select_asics):
        if select_asics is None:
            return self.list_asics[0]
        return select_asics

    def get_handle(self):
        self.handle = api.get_handle(self.card.macie_serial_number, self.connection)

    def get_available_macies(self):
        self.all_macies = api.get_available_macies(self.handle)
        self.list_macies = composite_byte_to_byte_list(self.all_macies)
        self.list_macies_index = byte_list_to_index_list(self.list_macies)
        self.print('Available MACIEs: {}'.format(self.list_macies_index))

    def select_macies(self, indices):
        return byte_list_to_composite_byte([self.list_macies[i] for i in indices])

    def get_available_asics(self):
        self.all_asics = api.get_available_asics(self.handle)
        self.list_asics = composite_byte_to_byte_list(self.all_asics)
        self.list_asics_index = byte_list_to_index_list(self.list_asics)
        self.print('Available ASICs: {}'.format(self.list_asics_index))

    def select_asics(self, indices):
        return byte_list_to_composite_byte([self.list_asics[i] for i in indices])

    def read_macie_register(self, address, select_macies=None):
        select_macies = self._get_read_select_macies(select_macies)
        return api.read_macie_register(self.handle, select_macies, address)

    def write_macie_register(self, address, value, select_macies=None):
        select_macies = self._set_write_select_macies(select_macies)
        api.write_macie_register(self.handle, select_macies, address, value)

    def write_macie_block(self, starting_adress, values, select_macies=None):
        select_macies = self._set_write_select_macies(select_macies)
        api.write_macie_block(self.handle, select_macies, starting_adress, values)

    def read_macie_block(self, starting_address, num_read_registers, select_macies=None):
        select_macies = self._get_read_select_macies(select_macies)
        return api.read_macie_block(self.handle, select_macies, starting_address, num_read_registers)

    def load_macie_firmware(self, firmware_slot=True, select_macies=None):
        select_macies = self._set_write_select_macies(select_macies)
        api.load_macie_firmware(self.handle, select_macies, firmware_slot)

    def download_macie_file(self, register_file, select_macies=None):
        select_macies = self._set_write_select_macies(select_macies)
        api.download_macie_file(self.handle, select_macies, register_file)

    def get_acadia_address_increment(self, select_macies=None):
        select_macies = self._get_read_select_macies(select_macies)
        return api.get_acadia_address_increment(self.handle, select_macies)

    def set_acadia_address_increment(self, auto_address_increment, select_macies):
        select_macies = self._set_write_select_macies(select_macies)
        api.set_acadia_address_increment(self.handle, select_macies, auto_address_increment)

    def write_asic_register(self, address, value, select_asics=None):
        select_asics = self._set_write_select_asics(select_asics)
        api.write_asic_register(self.handle, select_asics, address, value, self.b_option)

    def read_asic_register(self, address, select_asics=None):
        select_asics = self._get_read_select_asics(select_asics)
        return api.read_asic_register(self.handle, select_asics, address, self.b_24_bit, self.b_option)

    def write_asic_block(self, starting_address, values, select_asics=None):
        select_asics = self._set_write_select_asics(select_asics)
        api.write_asic_block(self.handle, select_asics, starting_address, values, self.b_option)

    def read_asic_block(self, starting_address, num_read_registers, select_asics=None):
        select_asics = self._get_read_select_asics(select_asics)
        return api.read_asic_block(
            self.handle, select_asics, starting_address, num_read_registers, self.b_24_bit, self.b_option
        )

    def download_asic_file(self, register_file, select_asics=None):
        select_asics = self._set_write_select_asics(select_asics)
        api.download_asic_file(self.handle, select_asics, register_file, self.b_option)

    def close_port(self):
        api.close_port(self.handle)

    def reset_error_counters(self, select_macies=None):
        select_macies = self._set_write_select_macies(select_macies)
        api.reset_error_counters(self.handle, select_macies)

    def set_macie_phase_shift(self, clock_phase, select_macies=None):
        select_macies = self._set_write_select_macies(select_macies)
        api.set_macie_phase_shift(self.handle, select_macies, clock_phase)

    def get_macie_phase_shift(self, select_macies=None):
        select_macies = self._get_read_select_macies(select_macies)
        return api.get_macie_phase_shift(self.handle, select_macies)

    def download_load_file(self, register_file, select_macies=None, select_asics=None):
        select_macies = self._set_write_select_macies(select_macies)
        select_asics = self._set_write_select_asics(select_asics)
        if not os.path.isfile(register_file.replace('/', os.path.sep)):
            raise FileNotFoundError(register_file)
        api.download_load_file(self.handle, select_macies, select_asics, register_file, self.b_option)

    def get_error_counters(self, select_macies=None):
        select_macies = self._get_read_select_macies(select_macies)
        return api.get_error_counters(self.handle, select_macies)

    def configure_camlink_interface(self, select_macies=None,):
        select_macies = self._get_read_select_macies(select_macies)
        api.configure_camlink_interface(
            self.handle, select_macies, self.mode, self.dcf_file, self.timeout, self.frame_x, self.frame_y
        )

    def configure_gige_science_interface(self, remote_port=43207, select_macies=None):
        select_macies = self._set_write_select_macies(select_macies)
        self.print(
            "configure_gige_science_interface handle: {}, macies: {}, mode: {}, frame_size: {}, remote_port: {}".format(
                self.handle, select_macies, self.mode, self.total_frame_size, remote_port
            )
        )
        api.configure_gige_science_interface(
            self.handle, select_macies, self.mode, self.total_frame_size, remote_port
        )

    def configure_usb_science_interface(self, select_macies=None):
        select_macies = self._set_write_select_macies(select_macies)
        api.configure_usb_science_interface(
            self.handle, select_macies, self.mode, self.total_frame_size, self.n_usb_science_buffers
        )

    def available_science_data(self):
        return api.available_science_data(self.handle)

    def available_science_frames(self):
        return api.available_science_frames(self.handle)

    def read_gige_science_frame(self):
        return api.read_gige_science_frame(self.handle, self.science_frame_timeout, self.total_frame_size)

    def read_usb_science_frame(self):
        return api.read_usb_science_frame(self.handle, self.science_frame_timeout, self.total_frame_size)

    def read_camlink_science_frame(self, tif_file_name=''):
        return api.read_camlink_science_frame(self.handle, self.science_frame_timeout, self.frame_size, tif_file_name)

    def write_fits_file(self, fits_file_name, frame_data, fits_header):
        api.write_fits_file(fits_file_name, self.frame_x, self.frame_y, frame_data, fits_header)

    def read_gige_science_data(self, n_science_words_read):
        return api.read_gige_science_data(self.handle, self.science_data_timeout, n_science_words_read)

    def read_usb_science_data(self, n_science_words_read):
        return api.read_usb_science_data(self.handle, self.science_data_timeout, n_science_words_read)

    def close_camlink_science_interface(self, select_macies=None):
        select_macies = self._set_write_select_macies(select_macies)
        api.close_camlink_science_interface(self.handle, select_macies)

    def close_gige_science_interface(self, select_macies=None):
        select_macies = self._set_write_select_macies(select_macies)
        api.close_gige_science_interface(self.handle, select_macies)

    def close_usb_science_interface(self, select_macies=None):
        select_macies = self._set_write_select_macies(select_macies)
        api.close_usb_science_interface(self.handle, select_macies)

    def set_voltage(self, power_id, power_value, select_macies=None):
        select_macies = self._set_write_select_macies(select_macies)
        api.set_voltage(self.handle, select_macies, power_id, power_value)

    def get_voltage(self, power_id, select_macies=None):
        select_macies = self._get_read_select_macies(select_macies)
        return api.get_voltage(self.handle, select_macies, power_id)

    def enable_power(self, power_control_ids, select_macies=None):
        select_macies = self._set_write_select_macies(select_macies)
        api.enable_power(self.handle, select_macies, power_control_ids)

    def disable_power(self, power_control_ids, select_macies=None):
        select_macies = self._set_write_select_macies(select_macies)
        api.disable_power(self.handle, select_macies, power_control_ids)

    def set_power(self, power_id, power_state, select_macies=None):
        select_macies = self._set_write_select_macies(select_macies)
        api.set_power(self.handle, select_macies, power_id, power_state)

    def get_power(self, power_id, select_macies=None):
        select_macies = self._get_read_select_macies(select_macies)
        return api.get_power(self.handle, select_macies, power_id)

    def set_telemetry_configuration(
            self, v_sample_rate, v_average, i_sample_rate, i_average, ground_reference, select_macies=None
    ):
        select_macies = self._set_write_select_macies(select_macies)
        api.set_telemetry_configuration(
            self.handle, select_macies, v_sample_rate, v_average, i_sample_rate, i_average, ground_reference
        )

    def get_telemetry_configuration(self, select_macies=None):
        select_macies = self._get_read_select_macies(select_macies)
        return api.get_telemetry_configuration(self.handle, select_macies)

    def get_telemetry(self, tlm_id, select_macies=None):
        select_macies = self._get_read_select_macies(select_macies)
        return api.get_telemetry(self.handle, select_macies, tlm_id)

    def get_telemetry_set(self, tlm_ids, select_macies=None):
        select_macies = self._get_read_select_macies(select_macies)
        return api.get_telemetry_set(self.handle, select_macies, tlm_ids)

    def get_telemetry_all(self, select_macies=None):
        select_macies = self._get_read_select_macies(select_macies)
        return api.get_telemetry_all(self.handle, select_macies)


class USBMACIE(BaseMACIE):
    def __init__(
            self, card=None, frame_x=4224, frame_y=4096, b_option=True, b_24_bit=0, n_science_headers=0,
            remove_science_headers=True
    ):
        super(USBMACIE, self).__init__(
            card, frame_x, frame_y, b_option, b_24_bit, n_science_headers, remove_science_headers
        )
        self.connection = api.Connection.USB
        self.mode = 2**8

    def generate_configure_mode(self):
        pass

    def configure_science_interface(self, select_macies=None):
        self.configure_usb_science_interface(select_macies=select_macies)

    def read_science_frame(self):
        return self.read_usb_science_frame()

    def read_science_data(self, n_science_words_read):
        return self.read_usb_science_data(n_science_words_read)

    def close_science_interface(self, select_macies=None):
        self.close_usb_science_interface(select_macies)


class GigeMACIE(BaseMACIE):
    def __init__(
            self, card=None, frame_x=4224, frame_y=4096, b_option=True, b_24_bit=0, n_science_headers=0,
            remove_science_headers=True
    ):
        super(GigeMACIE, self).__init__(
            card, frame_x, frame_y, b_option, b_24_bit, n_science_headers, remove_science_headers
        )
        self.connection = api.Connection.GigE

    def generate_configure_mode(self):
        pass

    def configure_science_interface(self, select_macies=None):
        self.configure_gige_science_interface(select_macies=select_macies)

    def read_science_frame(self):
        return self.read_gige_science_frame()

    def read_science_data(self, n_science_words_read):
        return self.read_gige_science_data(n_science_words_read)

    def close_science_interface(self, select_macies=None):
        self.close_gige_science_interface(select_macies)


class CamlinkMACIE(BaseMACIE):
    def __init__(
            self, card=None, frame_x=4224, frame_y=4096, b_option=True, b_24_bit=0, n_science_headers=0,
            remove_science_headers=True
    ):
        super(CamlinkMACIE, self).__init__(
            card, frame_x, frame_y, b_option, b_24_bit, n_science_headers, remove_science_headers
        )
        self.connection = api.Connection.UART

    def generate_configure_mode(self):
        pass

    def configure_science_interface(self, select_macies=None):
        self.configure_camlink_interface(select_macies=select_macies)

    def read_science_frame(self, tif_file_name=''):
        return self.read_camlink_science_frame(tif_file_name)

    def read_science_data(self, n_science_words_read):
        # TODO: add read_camlink_science_data when this is added to the MACIE api
        pass

    def close_science_interface(self, select_macies=None):
        self.close_camlink_science_interface(select_macies)


class BaseACADIA(BaseMACIE):
    def __init__(
            self, card=None, frame_x=4224, frame_y=4096, b_option=True, b_24_bit=0, n_science_headers=0,
            remove_science_headers=True
    ):
        super(BaseACADIA, self).__init__(
            card, frame_x, frame_y, b_option, b_24_bit, n_science_headers, remove_science_headers
        )
        self.asic_type = 0xacda
        self.sync_file = os.path.join(os.path.dirname(api.__file__), 'loadfiles', 'sce_resync.glf')

    def init(self, firmware_slot=True, load_files=tuple(), request=None, status=None):
        super(BaseACADIA, self).init(firmware_slot, load_files, request, status)
        # time.sleep(5)
        # self.sync(request, status)

    def start_asic_acquisition(self, data_frames, reset_frame_filenames=tuple(), reset_headers=tuple()):
        self.write_asic_register(self.settings['ASICREADFRAMESADDRESS'], data_frames)  # set number of data frames
        self.print('initializing acquire with {} data frames'.format(data_frames))
        # set number of reset frames
        self.write_asic_register(self.settings['ASICRESETFRAMESADDRESS'], self.reset_frames)
        self.print('initializing acquire with {} reset frames'.format(self.reset_frames))
        self.print('starting detector pixel reset and acadia acquire')
        # start asic data acquistion
        self.write_asic_register(self.settings['ASICSTARTACQUSITIONADDRESS'], self.settings['ASICSTARTACQUSITIONVALUE'])

    def parse_science_header(self, frame, cam_name, cam_index):
        science_header = {}
        if self.n_science_headers == 6:
            science_words = frame[self.settings['ASICIDLOWERTELEMETRYROW']][:self.n_science_headers]
            word1, word2, word3, word4, word5, word6 = science_words
            for i, science_word in enumerate(science_words):
                science_header["SCIWRD{}".format(i+1)] = science_word
            science_header['ABLKLEN'] = word1 & int('1' * 14, 2)
            science_header['ABLKCNT'] = word2 & int('0' * 3 + '0' * 4 + '1' * 8, 2)
            science_header['AASICID'] = word2 & int('0' * 3 + '1' * 4 + '0' * 8, 2)
            science_header['AHDRLEN'] = word2 & int('1' * 3 + '0' * 4 + '0' * 8, 2)
            science_header['ASDPCNT'] = word3 & int('0' * 1 + '0' * 1 + '0' * 1 + '1' * 13, 2)
            science_header['AFF'] = word3 & int('0' * 1 + '0' * 1 + '1' * 1 + '0' * 13, 2)
            science_header['ARDFRM'] = word3 & int('0' * 1 + '1' * 1 + '0' * 1 + '0' * 13, 2)
            science_header['AEXPVIDL'] = word3 & int('1' * 1 + '0' * 1 + '0' * 1 + '0' * 13, 2)
            science_header['ASCIFRM'] = word4 & int('0' * 7 + '1' * 9, 2)
            science_header['ASCIXPID'] = word4 & int('1' * 7 + '0' * 9, 2)
            chip_id_lower = word6
            try:
                chip_number = header.asic_chip_id_lower_matching[science_words['ASICIDLOWERTELEMETRYCOLUMN']]
            except KeyError as e:
                chip_number = cam_index
                # tb = traceback.format_exc()
                tb = 'chip number {} is not a stored value, fix this if you are using a new chip'.format(
                    hex(chip_id_lower)
                )
                error_log_and_print(tb, request=self.request)
                self.resync = True
            if chip_number != cam_index:
                self.print(
                    "De-shuffling: Chip number {} from telemetry doesn't match cam_index {}".format(
                        hex(chip_id_lower), cam_index
                    )
                )
                # error_log_and_print(
                #     "Chip number {} from telemetry doesn't match cam_index {}".format(hex(chip_id_lower), cam_index),
                #     request=self.request
                # )
            cam_index = chip_number
            cam_name = self.cam_names[cam_index]
        return science_header, cam_name, cam_index


class USBACADIA(BaseACADIA, USBMACIE):
    pass


class GigeACADIA(BaseACADIA, GigeMACIE):
    pass


class CamlinkACADIA(BaseACADIA, CamlinkMACIE):
    pass


def acadias_open(
        gige_command_port=0, ip_address_list=None, frame_x=4224, frame_y=4096, b_option=False, request=None,
        status=None, n_science_headers=0, remove_science_headers=True,
):
    if status is None:
        status = Status()
    api.init()
    # api.set_gige_timeout(1000)
    log_and_print('MACIE software opened', request=request)
    cards = api.check_interfaces(gige_command_port, ip_address_list)
    macie_interfaces = []
    # Choosing interface based on fastest communication speed
    _args = (frame_x, frame_y, b_option, 0, n_science_headers, remove_science_headers)
    for card in cards:
        if card.b_usb and card.usb_speed >= 3:
            macie_interface = USBACADIA(card, *_args)
            log_and_print(
                'MACIE {} USB connected at speed {}'.format(card.macie_serial_number, card.usb_speed), request=request
            )
        elif card.b_gige and card.gige_speed >= 1000:
            macie_interface = GigeACADIA(card, *_args)
            log_and_print(
                'MACIE {} Gige connected at speed {} via ip {}'.format(card.macie_serial_number, card.gige_speed, [card.ip_address[i] for i in range(4)]), request=request
            )
        elif card.b_usb:
            macie_interface = USBACADIA(card, *_args)
            log_and_print(
                'MACIE {} USB connected at speed {}'.format(card.macie_serial_number, card.usb_speed), request=request
            )
        elif card.b_gige:
            macie_interface = GigeACADIA(card, *_args)
            log_and_print(
                'MACIE {} Gige connected at speed {}'.format(card.macie_serial_number, card.gige_speed), request=request
            )
        elif card.b_uart:
            macie_interface = CamlinkACADIA(card, *_args)
            log_and_print(
                'MACIE {} USB connected at speed {}'.format(card.macie_serial_number, card.usb_speed), request=request
            )
        else:
            log_and_print(
                'MACIE {} Camlink connected'.format(card.macie_serial_number), request=request
            )
            continue
        macie_interface.open(request=request, status=status)
        macie_interfaces.append(macie_interface)
    # api.free()
    if not macie_interfaces:
        raise MissingMACIEError(
            'No MACIE interfaces found. Check that MACIEs are connected and powered on. IP address list: {}'.format(
                ip_address_list
            )
        )
    return macie_interfaces


def acadias_init(macie_interfaces, firmware_slot=True, load_files=tuple(), request=None, status=None):
    if status is None:
        status = Status()
    macie_interfaces_out = []

    # initializing detectors
    for macie_interface in macie_interfaces:
        assert isinstance(macie_interface, BaseMACIE)
        macie_interface.init(firmware_slot, load_files, request=request, status=status)
        macie_interfaces_out.append(macie_interface)

    # preparing detectors for data acquisition
    wait = load_settings()['INITWAIT']/1000
    log_and_print('After init wait {} seconds'.format(wait), request=request)
    time.sleep(wait)
    log_and_print('After init wait complete', request=request)
    log_and_print('After init test exposure', request=request)
    for macie_interface in macie_interfaces:
        macie_interface.start(
            macie_interface.settings['FRAMETIMESEC'], skip_time=0, request=request, status=status,
            save_science_frame=False
        )
    api.free()
    return macie_interfaces


def acadias_sync(macie_interfaces, request=None, status=None):
    if status is None:
        status = Status()
    for macie_interface in macie_interfaces:
        assert isinstance(macie_interface, BaseMACIE)
        macie_interface.sync(request=request, status=status)
    api.free()


def acadias_close(macie_interfaces, request=None, status=None):
    if status is None:
        status = Status()
    api.init()
    for macie_interface in macie_interfaces:
        assert isinstance(macie_interface, BaseMACIE)
        macie_interface.close(request=request, status=status)
    api.free()


def acadias_acquire(macie_interfaces, exposure_time, skip_time, request=None, status=None):
    if status is None:
        status = Status()
    for macie_interface in macie_interfaces:
        assert isinstance(macie_interface, BaseMACIE)
        macie_interface.start(exposure_time, skip_time=skip_time, request=request, status=status)
        # macie_interface.start(exposure_time, skip_time=skip_time, request=request, status=status)
        if macie_interface.resync and macie_interface.settings['AUTORESYNC']:
            macie_interface.print('ACADIAs out of sync, resyncing....')
            acadias_init(
                [macie_interface], macie_interface.settings['MACIEFIRMWARESLOT'],
                macie_interface.settings['MACIELOADFILES'], request, status
            )


def load_interface(macie_interface_file_name, request=None, status=None):
    if status is None:
        status = Status()
    assert isinstance(macie_interface_file_name, str)
    split_name = macie_interface_file_name.split('.')
    asic = int(split_name[-2], base=16)
    conn = int(split_name[-3])
    macie_types = [BaseMACIE, CamlinkMACIE, GigeMACIE, USBMACIE, BaseACADIA, CamlinkACADIA, GigeACADIA, USBACADIA]
    for macie_type in macie_types:
        macie_interface = macie_type()
        if macie_interface.asic_type == asic and int(macie_interface.connection) == conn:
            macie_interface.load(macie_interface_file_name, request=request, status=status)
            return macie_interface


macie_interface_storage_filename = os.path.join(macie_save_interfaces_dir, 'opened_interfaces.txt')


def gen_macie_interface_storage_file(filenames):
    with open(macie_interface_storage_filename, 'w') as f:
        f.writelines(filenames)


def load_macie_interfaces_from_storage_file(request=None):
    with open(macie_interface_storage_filename, 'r') as f:
        filenames = f.readlines()
    return [load_interface(f, request=request) for f in filenames]


def gen_frame_header(macie_interface):
    return fits.Header()


def gen_cam_names(index_list, cam_name_list):
    return [cam_name_list[index] for index in index_list]


def raise_test_error(error):
    _settings = load_settings()
    if _settings['ENABLETESTERRORS']:
        test_error_list = [error.upper() for error in _settings['TESTERRORS']]
        error = error.upper()
        if error in test_error_list:
            _test_error_dict = {
                'BADOPEN': MissingMACIEError,
                'BADHANDLE': api.MACIEFailError,
                'TIMEOUT': TimeoutError,
                'BADINIT': api.MACIEFailError,
                'BADCLOSE': api.MACIEFailError,
                'BADMODE': Exception,
                'BADSTART': api.ImageAcquisitionError,
                'BADSYNC': api.MACIEFailError,
                'BADCONFIG': Exception
            }
            raise _test_error_dict[error]


def io_open(request=None, status=None):
    if status is None:
        status = Status()

    raise_test_error('BADOPEN')
    raise_test_error('BADHANDLE')
    raise_test_error('TIMEOUT')

    _settings = load_settings()
    macie_interfaces = acadias_open(
        ip_address_list=_settings['MACIEIPLIST'], request=request, frame_x=_settings['FRAMEX'],
        frame_y=_settings['FRAMEY'], b_option=_settings['MACIEBOPTION'],
        gige_command_port=_settings['MACIEGIGECOMMANDPORT'], status=status,
        n_science_headers=_settings['NUMBEROFSCIENCEHEADERSPERROW'],
        remove_science_headers=_settings['REMOVESCIENCEHEADERS'],
    )
    save_files = [macie_interface.save() for macie_interface in macie_interfaces]
    gen_macie_interface_storage_file(save_files)


def io_init(request=None, status=None):
    if status is None:
        status = Status()

    raise_test_error('BADINIT')
    raise_test_error('BADHANDLE')
    raise_test_error('TIMEOUT')

    _settings = load_settings()
    interfaces = load_macie_interfaces_from_storage_file(request)
    init_interfaces = acadias_init(
        interfaces, load_files=_settings['MACIELOADFILES'], firmware_slot=_settings['MACIEFIRMWARESLOT'],
        request=request, status=status
    )
    save_files = [macie_interface.save() for macie_interface in init_interfaces]
    gen_macie_interface_storage_file(save_files)


def io_sync(request=None, status=None):
    if status is None:
        status = Status()

    raise_test_error('BADSYNC')
    raise_test_error('BADHANDLE')
    raise_test_error('TIMEOUT')

    _settings = load_settings()
    interfaces = load_macie_interfaces_from_storage_file(request)
    acadias_sync(interfaces, request=request, status=status)


def io_start(exposure_time, skip_time=0, request=None, status=None):
    if status is None:
        status = Status()

    raise_test_error('BADSTART')
    raise_test_error('BADHANDLE')
    raise_test_error('TIMEOUT')

    interfaces = load_macie_interfaces_from_storage_file(request=request)
    # science_frames = calc_num_frames(exposure_time)
    # macie_interface = interfaces[0]  # TODO: set this up to use multiple interfaces in parallel
    acadias_acquire(interfaces, exposure_time, skip_time, request, status)
    # macie_interface.start(exposure_time, skip_time=skip_time, request=request, status=status)


def io_close(request=None, status=None):
    if status is None:
        status = Status()

    raise_test_error('BADCLOSE')
    raise_test_error('BADHANDLE')
    raise_test_error('TIMEOUT')

    interfaces = load_macie_interfaces_from_storage_file(request=request)
    acadias_close(interfaces, request=request, status=status)
    # os.remove(macie_interface_storage_filename)


def io_config(request=None, status=None):
    if status is None:
        status = Status()

    raise_test_error('BADCONFIG')
    raise_test_error('BADHANDLE')
    raise_test_error('TIMEOUT')

    log_and_print("Not implemented for MACIE system", request=request)
