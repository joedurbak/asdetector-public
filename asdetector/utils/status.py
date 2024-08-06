from datetime import datetime as dt
import json

from asdetector.utils.files import gen_status_file_name, gen_status_file, JSONHandler


class Status:
    def __init__(self):
        self.json_handler = JSONHandler(gen_status_file_name())
        self.status = {}

    def get_status(self):
        self.status = self.json_handler.json_dict_from_file()
        return self.status

    def get_status_str(self):
        return json.dumps(self.status)

    def update_command_complete(self, complete=True):
        _dict = self.status
        _dict['CommandComplete'] = complete
        _dict['CommandCompleteTime'] = dt.isoformat(dt.now())
        self.json_handler.save_dict_to_json(_dict)

    def update_exposure_time_remaining(self, exposure_time):
        # _dict = self.status
        self.status['ExposureTimeRemaining'] = exposure_time
        # self.json_handler.save_dict_to_json(_dict)

    def update_total_frame_count(self, frame_count):
        # _dict = self.get_status()
        self.status['TotalFrameCount'] = frame_count
        # self.json_handler.save_dict_to_json(_dict)

    def update_exposure_frames(self, frame_file, camera_number):
        # _dict = self.get_status()
        self.status['ExposureFrames']['CAMERA{}'.format(camera_number)].append(frame_file)
        # self.json_handler.save_dict_to_json(_dict)

    def update_intermediate_reduced_frame_frames(self, frame_file, camera_number):
        # _dict = self.get_status()
        self.status['IntermediateReducedFrames']['CAMERA{}'.format(camera_number)].append(frame_file)
        # self.json_handler.save_dict_to_json(_dict)

    def update_final_reduced_exposure(self, frame_file, camera_number):
        # _dict = self.get_status()
        self.status['FinalReducedFrame']['CAMERA{}'.format(camera_number)] = frame_file
        # self.json_handler.save_dict_to_json(_dict)

    def update_current_command(self, command):
        gen_status_file()
        _dict = self.get_status()
        _dict['CurrentCommand'] = command
        _dict['CommandStartTime'] = dt.isoformat(dt.now())
        self.json_handler.save_dict_to_json(_dict)

#
# def get_status():
#     return json_dict_from_file()
#
#
# def get_status_str():
#     _dict = get_status()
#     return json.dumps(_dict)
#
#
# def update_command_complete(complete=True):
#     _dict = get_status()
#     _dict['CommandComplete'] = complete
#     _dict['CommandCompleteTime'] = dt.isoformat(dt.now())
#     save_dict_to_json(_dict)
#
#
# def update_exposure_time_remaining(exposure_time):
#     _dict = get_status()
#     _dict['ExposureTimeRemaining'] = exposure_time
#     save_dict_to_json(_dict)
#
#
# def update_total_frame_count(frame_count):
#     _dict = get_status()
#     _dict['TotalFrameCount'] = frame_count
#     save_dict_to_json(_dict)
#
#
# def update_exposure_frames(frame_file, camera_number):
#     _dict = get_status()
#     _dict['ExposureFrames']['CAMERA{}'.format(camera_number)].append(frame_file)
#     save_dict_to_json(_dict)
#
#
# def update_intermediate_reduced_frame_frames(frame_file, camera_number):
#     _dict = get_status()
#     _dict['IntermediateReducedFrames']['CAMERA{}'.format(camera_number)].append(frame_file)
#     save_dict_to_json(_dict)
#
#
# def update_final_reduced_exposure(frame_file, camera_number):
#     _dict = get_status()
#     _dict['FinalReducedFrame']['CAMERA{}'.format(camera_number)] = frame_file
#     save_dict_to_json(_dict)
#
#
# def update_current_command(command):
#     gen_status_file()
#     _dict = get_status()
#     _dict['CurrentCommand'] = command
#     _dict['CommandStartTime'] = dt.isoformat(dt.now())
#     save_dict_to_json(_dict)
