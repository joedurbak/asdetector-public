# from six.moves.collections_abc import Iterable
import os
from random import randint
import re
from threading import Lock

from astropy.io import fits
from matplotlib import pyplot as plt
import numpy as np
from PIL import Image

from asdetector.utils.files import load_settings


def gen_fits_header(header_dict):
    header_cards = []
    for key, item in header_dict.items():
        # print(key, item)
        header_cards.append((key, item['value'], item['comment']))
    return fits.Header(cards=header_cards)


class EmptyImageError(Exception):
    """Error when image is missing from fits file"""
    pass


class BaseImage:
    """
    BaseImage class creates an object with all of the general image manipulation techniques
    """
    def __init__(self, bad_pixel_map=None):
        self.image = None
        self.image_hdu = 0
        self.header = fits.Header()
        self.bad_pixel_map = bad_pixel_map

    def generate_bad_pixel_map(self):
        if self.bad_pixel_map is None:
            self.bad_pixel_map = np.zeros(self.image.shape)
        else:
            self.bad_pixel_map = image_file_or_array_to_array(self.bad_pixel_map)

    def show(self):
        """
        Displays the current image using pyplot
        """
        plt.figure(randint(0, 256))
        plt.imshow(self.image,)
        plt.xticks([]), plt.yticks([])
        plt.show()

    def save(self, filename, hdu=None):
        """
        saves image and header to fits file

        Parameters
        ----------
        filename : str
            file path to save to
        hdu : int
            image hdu number

        Returns
        -------

        """
        file_dir = os.path.dirname(filename)
        if hdu is None:
            hdu = self.image_hdu
        if not os.path.exists(file_dir):
            os.makedirs(file_dir)
        # print(self.header)
        hdu_primary = fits.PrimaryHDU(header=self.header)
        # hdu_primary = fits.PrimaryHDU()
        if hdu == 0:
            hdu_primary.data = self.image
            hdu_list = fits.HDUList([hdu_primary])
        else:
            hdu_image = fits.ImageHDU(self.image)
            hdu_list = fits.HDUList([hdu_primary, hdu_image])
        hdu_list.writeto(filename, overwrite=True, output_verify='silentfix')

    def histogram(
            self, bin_width='auto', histogram_range=(), x_range=(), y_range=(), show_plot=False, save_plot=False,
            save_filepath="histogram.txt"
    ):
        """
        creates intensity histogram of the image

        Parameters
        ----------
        bin_width : int or sequence or str, optional
            width of histogram bins
        histogram_range :
        x_range :
        y_range :
        show_plot :
        save_plot :
        save_filepath :

        Returns
        -------

        """
        if histogram_range == ():
            histogram_range = (self.image.min(), self.image.max())
        y_max, x_max = self.image.shape
        if x_range == ():
            x_range = (0, x_max-1)
        if y_range == ():
            y_range = (0, y_max-1)
        a = self.image[y_range[0]:y_range[1]][x_range[0]:x_range[1]]
        a = a.flatten()
        histogram = np.histogram(a, bin_width, histogram_range)
        if show_plot or save_plot:
            plt.figure(randint(0, 256))
            plt.hist(a, bin_width, histogram_range)
            plt.title('Image Intensity Histogram')
            plt.ylabel('Intensity')
            if show_plot:
                plt.show()
            if save_plot:
                plt.savefig(save_filepath)
        return histogram

    def slice(self, x_range=(), y_range=()):
        """
        Selects part of the image

        Parameters
        ----------
        x_range : Iterable
            min and max for slice
        y_range : Iterable
            min and max for slice

        Returns
        -------

        """
        # TODO: determine if we actually want it to replace the image, or return another array
        y_max, x_max = self.image.shape
        if x_range == ():
            x_range = (0, x_max)
        if y_range == ():
            y_range = (0, y_max)
        self.image = self.image[y_range[0]:y_range[1], x_range[0]:x_range[1]]

    def border(self, x_left=0, x_right=0, y_top=0, y_bottom=0, border_value=0):
        """
        adds a border around image

        Parameters
        ----------
        x_left : int
            adds border before 0th index along axis=1
        x_right : int
            adds border after maximum index along axis=1
        y_top : int
            adds border after maximum index along axis=0
        y_bottom : int
            adds border before 0th index along axis=0
        border_value : int or float
            pixel value of added border

        Returns
        -------

        """
        y_max, x_max = self.image.shape
        border_array = np.zeros((y_top+y_max+y_bottom, x_left+x_max+x_right)) + border_value
        border_array[y_bottom:y_bottom+y_max, x_left:x_left+x_max] = self.image
        self.image = border_array

    def resize(self, width_scale_factor=1, height_scale_factor=1):  # , resample=0):
        if width_scale_factor < 0:
            self.image = np.flip(self.image, 1)
            width_scale_factor = np.abs(width_scale_factor)
        if height_scale_factor < 0:
            self.image = np.flip(self.image, 0)
            height_scale_factor = np.abs(height_scale_factor)
        pil_image = Image.fromarray(self.image)
        width, height = pil_image.size
        width = width * width_scale_factor
        width = int(width)
        height = height * height_scale_factor
        height = int(height)
        pil_image_resize = pil_image.resize((width, height), resample=Image.NEAREST)
        # pil_image_resize = pil_image.resize((width, height), resample=Image.BICUBIC)
        self.image = np.array(pil_image_resize)

    def translate(self, x_translation, y_translation):
        self.image = np.roll(self.image, x_translation)
        self.image = np.roll(self.image, y_translation, axis=0)

    def crop_and_border(self, x_size, y_size, border_value=0):
        y_size_initial, x_size_initial = self.image.shape
        x_start = int((x_size_initial - x_size)/2)
        y_start = int((y_size_initial - y_size)/2)
        if x_start > 0:
            self.slice(x_range=(x_start, x_start+x_size))
        elif x_start < 0:
            x_start = -x_start
            x_size_difference = x_size - (2 * x_start + x_size_initial)
            self.border(
                x_left=x_start, x_right=x_start+x_size_difference, y_top=0, y_bottom=0, border_value=border_value
            )
        if y_start > 0:
            self.slice(y_range=(y_start, y_start+y_size))
        elif y_start < 0:
            y_start = -y_start
            y_size_difference = y_size - (2 * y_start + y_size_initial)
            self.border(
                x_left=0, x_right=0, y_top=y_start, y_bottom=y_start+y_size_difference, border_value=border_value
            )

    def scale_and_translate(
            self, x_translation=0, y_translation=0, x_scale=1, y_scale=1, border_value=0, x_size=None, y_size=None):
        # , resample=0):
        x_size_initial, y_size_initial = self.image.shape
        if x_size is None:
            x_size = x_size_initial
        if y_size is None:
            y_size = y_size_initial
        self.resize(x_scale, y_scale)  # , resample=resample)
        self.crop_and_border(x_size, y_size, border_value=border_value)
        self.translate(x_translation, y_translation)

    def power_pixel_scale(self, a=1000):
        x = self.image/np.max(self.image)
        self.image = (a**x-1)/a

    def linearity_correction(self):
        # TODO
        pass

    def min_max_intensity_manipulate(self, minimum, maximum):
        min_max_intensity_manipulate(self.image, minimum, maximum)

    def deinterlace(
            self, nch=load_settings()['NUMBEROFREADOUTCHANNELS'],
            nheaders=load_settings()['NUMBEROFSCIENCEHEADERSPERROW']
    ):
        """Deinterlaces detector data given 2D array and number of output
           channels."""
        no_header_image = self.image[:, nheaders:]
        data_dein = 0.0 * no_header_image
        nch_pix = int(no_header_image.shape[1] / nch)
        for i in range(nch):
            if i % 2 == 0:
                data_dein[:, i * nch_pix:(i + 1) * nch_pix] = no_header_image[:, i::nch]
            else:
                data_dein[:, (i + 1) * nch_pix - 1:i * nch_pix - 1:-1] = no_header_image[:, i::nch]
        self.image[:, nheaders:] = data_dein


class ExistingImage(BaseImage):
    def __init__(self, filename: str, bad_pixel_map=None, fits_image_hdu=0):
        super(ExistingImage, self).__init__(bad_pixel_map)
        self.image_hdu = fits_image_hdu
        self.filename = filename
        self.hdu_list = fits.open(filename)
        self.image = self.hdu_list[self.image_hdu].data
        if self.image is None:
            raise EmptyImageError("Selected image HDU contains no array")
        self.header = self.hdu_list[0].header
        self.generate_bad_pixel_map()
        self.hdu_list.close()


class PNGImage(BaseImage):
    def __init__(self, filename, bad_pixel_map=None):
        super(PNGImage, self).__init__(bad_pixel_map=bad_pixel_map)
        self.image = np.mean(plt.imread(filename,), -1)


class ArrayImage(BaseImage):
    def __init__(self, array, bad_pixel_map=None):
        super(ArrayImage, self).__init__(bad_pixel_map=bad_pixel_map)
        self.image = array
        self.generate_bad_pixel_map()


class ListImage(BaseImage):
    def __init__(self, images, bad_pixel_map=None):
        super(ListImage, self).__init__(bad_pixel_map=bad_pixel_map)
        self.images = np.asarray([image.image for image in images])

    def linearity_check(self):
        pass


class CombinedImage(ListImage):
    def __init__(self, images, bad_pixel_map=None):
        super(CombinedImage, self).__init__(images, bad_pixel_map=bad_pixel_map)
        self.image = np.mean(self.images, axis=0)
        self.generate_bad_pixel_map()


def image_overlay(background_image, foreground_image, background_cmap='Greys'):
    """
    Plots foreground over background image

    Parameters
    ----------
    background_image : np.array
    foreground_image : np.array
    background_cmap : string

    Returns
    -------

    """
    plt.figure()
    plt.imshow(background_image, interpolation='nearest', cmap=background_cmap)
    plt.imshow(foreground_image, interpolation='bilinear', alpha=0.5)
    plt.yticks([])
    plt.xticks([])
    plt.show()


def file_overlay(background_file, foreground_file, background_cmap='Greys'):
    background_image = ExistingImage(background_file).image
    foreground_image = ExistingImage(foreground_file).image
    image_overlay(background_image, foreground_image, background_cmap)


def min_max_intensity_manipulate(image, minimum, maximum):
    image[image < minimum] = minimum
    image[image > maximum] = maximum


def image_file_or_array_to_array(file_or_array):
    if type(file_or_array) is str:
        if file_or_array.endswith('.fits'):
            return ExistingImage(file_or_array).image
    elif type(file_or_array) is np.ndarray:
        return file_or_array
    else:
        raise TypeError("{} isn't a fits file or a numpy array".format(file_or_array))


def imshow_with_labels(image, intensity_label='Intensity', vmin=None, vmax=None, xmin=0, xmax=None, ymin=0, ymax=None):
    plt.imshow(np.flip(image, 1), vmin=vmin, vmax=vmax, cmap='rainbow', origin='upper')  # extent=(xmin, xmax, ymax, ymin))
    plt.xlabel('x (pixels)')
    plt.ylabel('y (pixels)')
    cbar = plt.colorbar()
    cbar.ax.set_ylabel(intensity_label)
    plt.show()


def file_imshow_with_labels(
        image_file, image_hdu=0, intensity_label='Intensity', vmin=None, vmax=None, xmin=0, xmax=None, ymin=0, ymax=None
):
    image = ExistingImage(image_file, fits_image_hdu=image_hdu).image
    imshow_with_labels(image, intensity_label, vmin, vmax, xmin, xmax, ymin, ymax,)


def get_fits_image_array(fits_file, image_hdu=0):
    hdu_list = fits.open(fits_file)
    data = hdu_list[image_hdu].data
    hdu_list.close()
    return data


def get_images_from_dir(image_dir, image_hdu=0, prefix=''):
    ls = os.listdir(image_dir)
    ls.sort()
    ls = [os.path.join(image_dir, f) for f in ls if (f.endswith('.fits') and f.startswith(prefix))]
    return np.asarray([get_fits_image_array(f, image_hdu) for f in ls])


def get_combination_header_from_dir(image_dir, image_hdu):
    return fits.Header()


def cds_frame_reduce(images):
    image_type = str(images[0].dtype)
    if image_type.startswith('u'):
        image_type = image_type[1:]
        precision = int(re.findall(r'\d+', image_type)[-1])
        image_type = image_type.replace(str(precision), str(precision*2))

    return images[-1].astype(image_type) - images[0].astype(image_type)


def ssr_frame_reduce(images):
    return images[-1]


def mean_frame_reduce(images):
    return images.mean(axis=0)


def mode_frame_reduce(images):
    return images.mode(axis=0)


def max_frame_reduce(images):
    return images.max(axis=0)


def min_frame_reduce(images):
    return images.min(axis=0)


def median_frame_reduce(images):
    return images.median(axis=0)


def fowler_frame_reduce(images, fowler_number):
    start = images[0:fowler_number].mean(axis=0)
    end = images[-1-fowler_number:-1].mean(axis=0)
    return end - start


def fowler2_frame_reduce(images):
    return fowler_frame_reduce(images, 2)


def fowler4_frame_reduce(images):
    return fowler_frame_reduce(images, 4)


def fowler8_frame_reduce(images):
    return fowler_frame_reduce(images, 8)


def fowler16_frame_reduce(images):
    return fowler_frame_reduce(images, 16)


FRAME_REDUCE_METHODS = {
    'CDS': cds_frame_reduce,
    'SSR': ssr_frame_reduce,
    'MEAN': mean_frame_reduce,
    'MEDIAN': median_frame_reduce,
    'MODE': mode_frame_reduce,
    'MIN': min_frame_reduce,
    'MAX': max_frame_reduce,
    'FOWLER2': fowler2_frame_reduce,
    'FOWLER4': fowler4_frame_reduce,
    'FOWLER8': fowler8_frame_reduce,
    'FOWLER16': fowler16_frame_reduce,
}


INTERMEDIATE_FRAME_REDUCE_METHODS = {
    'CDS': cds_frame_reduce,
    'SSR': ssr_frame_reduce,
    'MEAN': mean_frame_reduce,
    'MEDIAN': median_frame_reduce,
    'MODE': mode_frame_reduce,
    'MIN': min_frame_reduce,
    'MAX': max_frame_reduce,
    'FOWLER2': cds_frame_reduce,
    'FOWLER4': cds_frame_reduce,
    'FOWLER8': cds_frame_reduce,
    'FOWLER16': cds_frame_reduce,
}


def reduce_image_from_array(image_array):
    return FRAME_REDUCE_METHODS[load_settings()['MODE']](image_array)


def intermediate_reduce_image_from_array(image_array):
    return INTERMEDIATE_FRAME_REDUCE_METHODS[load_settings()['MODE']](image_array)


def reduce_image_from_dir(image_dir, image_hdu=0, image_prefix=''):
    images = get_images_from_dir(image_dir, image_hdu, image_prefix)
    combination_header = get_combination_header_from_dir(image_dir, image_hdu)
    return reduce_image_from_array(images), combination_header


def intermediate_reduce_image_from_dir(image_dir, image_hdu=0, image_prefix=''):
    images = get_images_from_dir(image_dir, image_hdu, image_prefix)
    if len(images) < 1:
        return ssr_frame_reduce(images)
    return intermediate_reduce_image_from_array(images)


def ssr_calc_frames(exposure_time, time_per_frame):
    return int(round(exposure_time / time_per_frame))


def cds_calc_frames(exposure_time, time_per_frame):
    return int(ssr_calc_frames(exposure_time, time_per_frame) + 1)


def mean_calc_frames(exposure_time, time_per_frame):
    return int(ssr_calc_frames(exposure_time, time_per_frame) * 2)


def fowler_calc_frames(exposure_time, time_per_frame, fowler_number):
    fowler_time = time_per_frame * fowler_number
    exposure_time_remaining = exposure_time - fowler_time
    if exposure_time_remaining < 0:
        print('{} s is less than the minimum exposure time for fowler {} sampling'.format(exposure_time, fowler_number))
        print('Doing an exposure of {} s instead'.format(fowler_time))
        return fowler_number * 2
    return int(ssr_calc_frames(exposure_time_remaining, time_per_frame) + fowler_number*2)


def fowler2_calc_frames(exposure_time, time_per_frame):
    return fowler_calc_frames(exposure_time, time_per_frame, 2)


def fowler4_calc_frames(exposure_time, time_per_frame):
    return fowler_calc_frames(exposure_time, time_per_frame, 4)


def fowler8_calc_frames(exposure_time, time_per_frame):
    return fowler_calc_frames(exposure_time, time_per_frame, 8)


def fowler16_calc_frames(exposure_time, time_per_frame):
    return fowler_calc_frames(exposure_time, time_per_frame, 16)


FRAMES_PER_EXPOSURE_TIME = {
    'CDS': cds_calc_frames,
    'SSR': ssr_calc_frames,
    'MEAN': mean_calc_frames,
    'MEDIAN': mean_calc_frames,
    'MODE': mean_calc_frames,
    'MIN': ssr_calc_frames,
    'MAX': ssr_calc_frames,
    'FOWLER2': fowler2_calc_frames,
    'FOWLER4': fowler4_calc_frames,
    'FOWLER8': fowler8_calc_frames,
    'FOWLER16': fowler16_calc_frames,
}


def calc_num_frames(exposure_time):
    _settings = load_settings()
    return FRAMES_PER_EXPOSURE_TIME[_settings['MODE']](exposure_time, _settings['FRAMETIMESEC'])


def cds_calc_exposure(frames, time_per_frame):
    return (frames-1) * time_per_frame


def ssr_calc_exposure(frames, time_per_frame):
    return frames * time_per_frame


def mean_calc_exposure(frames, time_per_frame):
    return ssr_calc_exposure(frames, time_per_frame)/2


def fowler_calc_exposure(frames, time_per_frame, fowler_number):
    fowler_time = fowler_number * time_per_frame
    frame_time = (frames - 2 * fowler_number) * time_per_frame
    return fowler_time + frame_time


def fowler2_calc_exposure(frames, time_per_frame):
    return fowler_calc_exposure(frames, time_per_frame, 2)


def fowler4_calc_exposure(frames, time_per_frame):
    return fowler_calc_exposure(frames, time_per_frame, 4)


def fowler8_calc_exposure(frames, time_per_frame):
    return fowler_calc_exposure(frames, time_per_frame, 4)


def fowler16_calc_exposure(frames, time_per_frame):
    return fowler_calc_exposure(frames, time_per_frame, 4)


EXPOSURE_TIME_PER_FRAMES = {
    'CDS': cds_calc_exposure,
    'SSR': ssr_calc_exposure,
    'MEAN': mean_calc_exposure,
    'MEDIAN': mean_calc_exposure,
    'MODE': mean_calc_exposure,
    'MIN': ssr_calc_exposure,
    'MAX': ssr_calc_exposure,
    'FOWLER2': fowler2_calc_exposure,
    'FOWLER4': fowler4_calc_exposure,
    'FOWLER8': fowler8_calc_exposure,
    'FOWLER16': fowler16_calc_exposure,
}


def calc_effective_exposure_time(frames):
    _settings = load_settings()
    return EXPOSURE_TIME_PER_FRAMES[_settings['MODE']](frames, _settings['FRAMETIMESEC'])


class ImageHandler:
    def __init__(self):
        self.lock = Lock()

    def save_image(self, image_array, filename, fits_header=None):
        self.lock.acquire()
        img = ArrayImage(image_array)
        if fits_header is not None:
            if isinstance(fits_header, dict):
                fits_header = gen_fits_header(fits_header)
                img.header = fits_header
            elif isinstance(fits_header, fits.Header):
                img.header = fits_header
        img.save(filename)
        self.lock.release()
