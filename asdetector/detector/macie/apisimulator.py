# coding=utf-8
"""
Author: Joe Durbak
emails: joseph.m.durbak@nasa.gov, jmdurbak@terpmail.umd.edu, durbak.3@gmail.com
Last update: 2022-01-07

api.py is a full wrapper of the MACIE API software provided by Markury Scientific. Code assumes MACIE software
from Markury Scientific is already installed and in the PATH.

Based on v5.1 MACIE API
"""
import ctypes as ct
import sys
from collections import OrderedDict
from enum import Enum, IntEnum
from random import randint
from datetime import datetime as dt

import numpy as np

from asdetector.utils.files import load_settings

SETTINGS = load_settings()

MACIE_ATTRS = (
    'MACIE_LibVersion', 'MACIE_Init', 'MACIE_Free', 'MACIE_Error', 'MACIE_CheckInterfaces', 'MACIE_SetGigeTimeout',
    'MACIE_GetHandle', 'MACIE_GetAvailableMACIEs', 'MACIE_GetAvailableASICs', 'MACIE_ReadMACIEReg',
    'MACIE_WriteMACIEReg', 'MACIE_WriteMACIEBlock', 'MACIE_ReadMACIEBlock', 'MACIE_loadMACIEFirmware',
    'MACIE_DownloadMACIEFile', 'MACIE_WriteASICReg', 'MACIE_ReadASICReg', 'MACIE_WriteASICBlock',
    'MACIE_ReadASICBlock', 'MACIE_DownloadASICFile', 'MACIE_ClosePort', 'MACIE_ResetErrorCounters',
    'MACIE_SetMACIEPhaseShift', 'MACIE_GetMACIEPhaseShift', 'MACIE_DownloadLoadfile', 'MACIE_GetErrorCounters',
    'MACIE_ConfigureCamLinkInterface', 'MACIE_ConfigureGigeScienceInterface', 'MACIE_ConfigureUSBScienceInterface',
    'MACIE_AvailableScienceData', 'MACIE_AvailableScienceFrames', 'MACIE_ReadGigeScienceFrame',
    'MACIE_ReadCamlinkScienceFrame', 'MACIE_ReadUSBScienceFrame', 'MACIE_WriteFitsFile', 'MACIE_ReadGigeScienceData',
    'MACIE_ReadUSBScienceData', 'MACIE_CloseCamlinkScienceInterface', 'MACIE_CloseGigeScienceInterface',
    'MACIE_CloseUSBScienceInterface', 'MACIE_SetVoltage', 'MACIE_GetVoltage', 'MACIE_EnablePower', 'MACIE_DisablePower',
    'MACIE_SetPower', 'MACIE_GetPower', 'MACIE_SetTelemetryConfiguration', 'MACIE_GetTelemetryConfiguration',
    'MACIE_GetTelemetry', 'MACIE_GetTelemetrySet', 'MACIE_GetTelemetryAll', 'MACIE_GetAcadiaAddressIncrement',
    'MACIE_SetAcadiaAddressIncrement'
)


# Convenience functions
def list_to_array_pointer(list_or_tuple, c_type=ct.c_int):
    assert isinstance(list_or_tuple, list) or isinstance(list_or_tuple, tuple)
    n = len(list_or_tuple)
    p_type = c_type * n
    return ct.c_ushort(n), p_type(*list_or_tuple)


def structure_to_dict(structure):
    structure_dict = OrderedDict()
    _fields = structure._fields_
    for f, t in _fields:
        val = structure.__getattribute__(f)
        # print(f,t,val)
        if isinstance(f, ct.Structure):
            val = structure_to_dict(val)
        if isinstance(val, OrderedDict):
            structure_dict[f] = val
        else:
            try:
                structure_dict[f] = val.value
            except AttributeError:
                structure_dict[f] = val
    return structure_dict


# API specific type wrappers
class CtypesEnum(IntEnum):
    @classmethod
    def from_param(cls, obj):
        return int(obj)


class Connection(CtypesEnum):
    """
    macie.h
    -------
    typedef enum
    {
        MACIE_NONE,
        MACIE_USB,
        MACIE_GigE,
        MACIE_UART
    } MACIE_Connection;
    """
    NONE = 0
    USB = 1
    GigE = 2
    UART = 3


class Status(Enum):
    """
    macie.h
    -------
    typedef enum
    {
        MACIE_OK,
        MACIE_FAIL
    } MACIE_STATUS;
    """
    OK = 0
    FAIL = 1


class PowerDAC(CtypesEnum):
    """
    macie.h
    -------
    typedef enum
    {
        MACIE_DAC_MACIE_DAC_VREF1,    // Vref1,  0 - 4.095V, LSB = 1.00mV
        MACIE_DAC_VDDAHIGH1,          // VDDAHigh1, 0V - 4.089V, LSB = 1.08 mV
        MACIE_DAC_VDDAHIGH1_VL,       // VDDAHigh1 Overvoltage limit, 0 - 4.761V, LSB = 1.16mV
        MACIE_DAC_VDDAHIGH1_CL,       // VDDAHigh1 Current limit, 0 - 1023.8mA, LSB = 250µA
        MACIE_DAC_VDDALOW1,           // VDDALow1, 0V - 4.089V, LSB = 1.08 mV
        MACIE_DAC_VDDALOW1_VL,        // VDDALow1 Overvoltage limit, 0 - 4.761V, LSB = 1.16mV
        MACIE_DAC_VDDALOW1_CL,        // VDDALow1 Current limit, 0 - 1023.8mA, LSB = 250µA
        MACIE_DAC_VDDHIGH1,           // VDDHigh1, 0V - 4.089V, LSB = 1.08 mV
        MACIE_DAC_VDDHIGH1_VL,        // VDDHigh1 Overvoltage limit, 0 - 4.761V, LSB = 1.16mV
        MACIE_DAC_VDDHIGH1_CL,        // VDDHigh1 Current limit, 0 - 511.9mA, LSB = 125µA
        MACIE_DAC_VDDLOW1,            // VDDLow1, h000 = 4.089V, hed0 = 0V, LSB = 1.08 mV
        MACIE_DAC_VDDLOW1_VL,         // VDDLow1 Overvoltage limit, 0 - 4.761V, LSB = 1.16mV
        MACIE_DAC_VDDLOW1_CL,         // VDDLow1 Current limit, 0 - 511.9mA, LSB = 125µA
        MACIE_DAC_VDDIO1,             // VDDIO1, h000 = 4.089V, hed0 = 0V, LSB = 1.08 mV
        MACIE_DAC_VDDIO1_VL,          // VDDIO1 Overvoltage limit, 0 - 4.761V, LSB = 1.16mV
        MACIE_DAC_VDDIO1_CL,          // VDDIO1 Current limit, 0 - 511.9mA, LSB = 125µA
        MACIE_DAC_VSSIO1,             // VSSIO1, 0 - 4.095V, LSB = 1.00mV
        MACIE_DAC_VSSIO1_VL,          // VSSIO1 Overvoltage limit, 0 - 4.095V, LSB = 1.00mV
        MACIE_DAC_VDDAUX1,            // VDDAUX1, h000 = 4.089V, hed0 = 0V, LSB = 1.08 mV
        MACIE_DAC_VREF2,              // Same as VREF1
        MACIE_DAC_VDDAHIGH2,          // Same as VDDAHIGH1
        MACIE_DAC_VDDAHIGH2_VL,       // Same as VDDAHIGH1_VL
        MACIE_DAC_VDDAHIGH2_CL,       // Same as VDDAHIGH1_CL
        MACIE_DAC_VDDALOW2,           // Same as VDDALOW1
        MACIE_DAC_VDDALOW2_VL,        // Same as VDDALOW1_VL
        MACIE_DAC_VDDALOW2_CL,        // Same as VDDALOW1_CL
        MACIE_DAC_VDDHIGH2,           // Same as VDDHIGH1
        MACIE_DAC_VDDHIGH2_VL,        // Same as VDDHIGH1_VL
        MACIE_DAC_VDDHIGH2_CL,        // Same as VDDHIGH1_CL
        MACIE_DAC_VDDLOW2,            // Same as VDDLOW1
        MACIE_DAC_VDDLOW2_VL,         // Same as VDDLOW1_VL
        MACIE_DAC_VDDLOW2_CL,         // Same as VDDLOW1_CL
        MACIE_DAC_VDDIO2,             // Same as VDDIO1
        MACIE_DAC_VDDIO2_VL,          // Same as VDDIO1_VL
        MACIE_DAC_VDDIO2_CL,          // Same as VDDIO1_CL
        MACIE_DAC_VSSIO2,             // Same as VSSIO1
        MACIE_DAC_VSSIO2_VL,          // Same as VSSIO1_VL
        MACIE_DAC_VDDAUX2             // Same as VDDAUX1
    } MACIE_PWR_DAC;
    """
    DAC_MACIE_DAC_VREF1 = 0
    DAC_VDDAHIGH1 = 1
    DAC_VDDAHIGH1_VL = 2
    DAC_VDDAHIGH1_CL = 3
    DAC_VDDALOW1 = 4
    DAC_VDDALOW1_VL = 5
    DAC_VDDALOW1_CL = 6
    DAC_VDDHIGH1 = 7
    DAC_VDDHIGH1_VL = 8
    DAC_VDDHIGH1_CL = 9
    DAC_VDDLOW1 = 10
    DAC_VDDLOW1_VL = 11
    DAC_VDDLOW1_CL = 12
    DAC_VDDIO1 = 13
    DAC_VDDIO1_VL = 14
    DAC_VDDIO1_CL = 15
    DAC_VSSIO1 = 16
    DAC_VSSIO1_VL = 17
    DAC_VDDAUX1 = 18
    DAC_VREF2 = 19
    DAC_VDDAHIGH2 = 20
    DAC_VDDAHIGH2_VL = 21
    DAC_VDDAHIGH2_CL = 22
    DAC_VDDALOW2 = 23
    DAC_VDDALOW2_VL = 24
    DAC_VDDALOW2_CL = 25
    DAC_VDDHIGH2 = 26
    DAC_VDDHIGH2_VL = 27
    DAC_VDDHIGH2_CL = 28
    DAC_VDDLOW2 = 29
    DAC_VDDLOW2_VL = 30
    DAC_VDDLOW2_CL = 31
    DAC_VDDIO2 = 32
    DAC_VDDIO2_VL = 33
    DAC_VDDIO2_CL = 34
    DAC_VSSIO2 = 35
    DAC_VSSIO2_VL = 36
    DAC_VDDAUX2 = 37


class PowerControl(CtypesEnum):
    """
    macie.h
    -------
    typedef enum
    {
        MACIE_CTRL_5V_ASIC,
        MACIE_CTRL_GIGE,
        MACIE_CTRL_GIGE_OVERRIDE,
        MACIE_CTRL_DGND_FILTER_BYPASS,
        MACIE_CTRL_USB_FILTER_BYPASS,
        MACIE_CTRL_AGND_CLEAN_FILTER_BYPASS,
        MACIE_CTRL_AGND_DIRTY_FILTER_BYPASS,
        MACIE_CTRL_VDDAUX1,
        MACIE_CTRL_VDDAUX2,
        MACIE_CTRL_VDDAHIGH1,
        MACIE_CTRL_VDDALOW1,
        MACIE_CTRL_VREF1,
        MACIE_CTRL_SENSE_VREF1_GNDA,
        MACIE_CTRL_SENSE_VDDAHIGH1_GNDA,
        MACIE_CTRL_SENSE_VDDAHIGH1,
        MACIE_CTRL_SENSE_VDDALOW1_GNDA,
        MACIE_CTRL_SENSE_VDDALOW1,
        MACIE_CTRL_VDDHIGH1,
        MACIE_CTRL_VDDLOW1,
        MACIE_CTRL_VDDIO1,
        MACIE_CTRL_VSSIO1,
        MACIE_CTRL_SENSE_VDDHIGH1_GND,
        MACIE_CTRL_SENSE_VDDHIGH1,
        MACIE_CTRL_SENSE_VDDLOW1_GND,
        MACIE_CTRL_SENSE_VDDLOW1,
        MACIE_CTRL_VDDAHIGH2,
        MACIE_CTRL_VDDALOW2,
        MACIE_CTRL_VREF2,
        MACIE_CTRL_SENSE_VREF2_GNDA,
        MACIE_CTRL_SENSE_VDDAHIGH2_GNDA,
        MACIE_CTRL_SENSE_VDDAHIGH2,
        MACIE_CTRL_SENSE_VDDALOW2_GNDA,
        MACIE_CTRL_SENSE_VDDALOW2,
        MACIE_CTRL_VDDHIGH2,
        MACIE_CTRL_VDDLOW2,
        MACIE_CTRL_VDDIO2,
        MACIE_CTRL_VSSIO2,
        MACIE_CTRL_SENSE_VDDHIGH2_GND,
        MACIE_CTRL_SENSE_VDDHIGH2,
        MACIE_CTRL_SENSE_VDDLOW2_GND,
        MACIE_CTRL_SENSE_VDDLOW2
    } MACIE_PWR_CTRL;
    """
    CTRL_5V_ASIC = 0
    CTRL_GIGE = 1
    CTRL_GIGE_OVERRIDE = 2
    CTRL_DGND_FILTER_BYPASS = 3
    CTRL_USB_FILTER_BYPASS = 4
    CTRL_AGND_CLEAN_FILTER_BYPASS = 5
    CTRL_AGND_DIRTY_FILTER_BYPASS = 6
    CTRL_VDDAUX1 = 7
    CTRL_VDDAUX2 = 8
    CTRL_VDDAHIGH1 = 9
    CTRL_VDDALOW1 = 10
    CTRL_VREF1 = 11
    CTRL_SENSE_VREF1_GNDA = 12
    CTRL_SENSE_VDDAHIGH1_GNDA = 13
    CTRL_SENSE_VDDAHIGH1 = 14
    CTRL_SENSE_VDDALOW1_GNDA = 15
    CTRL_SENSE_VDDALOW1 = 16
    CTRL_VDDHIGH1 = 17
    CTRL_VDDLOW1 = 18
    CTRL_VDDIO1 = 19
    CTRL_VSSIO1 = 20
    CTRL_SENSE_VDDHIGH1_GND = 21
    CTRL_SENSE_VDDHIGH1 = 22
    CTRL_SENSE_VDDLOW1_GND = 23
    CTRL_SENSE_VDDLOW1 = 24
    CTRL_VDDAHIGH2 = 25
    CTRL_VDDALOW2 = 26
    CTRL_VREF2 = 27
    CTRL_SENSE_VREF2_GNDA = 28
    CTRL_SENSE_VDDAHIGH2_GNDA = 29
    CTRL_SENSE_VDDAHIGH2 = 30
    CTRL_SENSE_VDDALOW2_GNDA = 31
    CTRL_SENSE_VDDALOW2 = 32
    CTRL_VDDHIGH2 = 33
    CTRL_VDDLOW2 = 34
    CTRL_VDDIO2 = 35
    CTRL_VSSIO2 = 36
    CTRL_SENSE_VDDHIGH2_GND = 37
    CTRL_SENSE_VDDHIGH2 = 38
    CTRL_SENSE_VDDLOW2_GND = 39
    CTRL_SENSE_VDDLOW2 = 40


class TLMSampleRate(CtypesEnum):
    """
    macie.h
    -------
    typedef enum
    {
        MACIE_TLM_16p7_Hz,
        MACIE_TLM_20_Hz,
        MACIE_TLM_83p3_Hz,
        MACIE_TLM_167_Hz
    } MACIE_TLM_SAMPLE_RATE;
    """
    TLM_16p7_Hz = 0
    TLM_20_Hz = 1
    TLM_83p3_Hz = 2
    TLM_167_Hz = 3


class TLMAverage(CtypesEnum):
    """
    macie.h
    -------
    typedef enum
    {
        MACIE_TLM_AVG_1,
        MACIE_TLM_AVG_2,
        MACIE_TLM_AVG_4,
        MACIE_TLM_AVG_8
    } MACIE_TLM_AVERAGE;
    """
    TLM_AVG_1 = 0
    TLM_AVG_2 = 1
    TLM_AVG_4 = 2
    TLM_AVG_8 = 3


class TLMGroundReference(CtypesEnum):
    """
    macie.h
    -------
    typedef enum
    {
        MACIE_TLM_REF_GND, //GND, 1 = DGND, 2 = AGND_CLEAN, 3 = AGND_DIRTY
        MACIE_TLM_REF_DGND,
        MACIE_TLM_REF_AGND_CLEAN,
        MACIE_TLM_REF_AGND_DIRTY,
        MACIE_TLM_REF_AUTO_GROUND
    } MACIE_TLM_GROUND_REFERENCE;
    """
    TLM_REF_GND = 0
    TLM_REF_DGND = 1
    TLM_REF_AGND_CLEAN = 2
    TLM_REF_AGND_DIRTY = 3
    TLM_REF_AUTO_GROUND = 4


class TLMItem(CtypesEnum):
    """
    macie.h
    -------
    typedef enum
    {
        MACIE_TLM_V_VDDAHIGH1,
        MACIE_TLM_V_VDDAHIGH2,
        MACIE_TLM_V_VDDALOW1,
        MACIE_TLM_V_VDDALOW2,
        MACIE_TLM_V_VREF1,
        MACIE_TLM_V_VREF2,
        MACIE_TLM_V_VDDHIGH1,
        MACIE_TLM_V_VDDHIGH2,
        MACIE_TLM_V_VDDLOW1,
        MACIE_TLM_V_VDDLOW2,
        MACIE_TLM_V_VDDIO1,
        MACIE_TLM_V_VDDIO2,
        MACIE_TLM_V_VSSIO1,
        MACIE_TLM_V_VSSIO2,
        MACIE_TLM_V_VDDAUX1,
        MACIE_TLM_V_VDDAUX2,
        MACIE_TLM_V_GNDA1,
        MACIE_TLM_V_GNDA2,
        MACIE_TLM_V_GND1,
        MACIE_TLM_V_GND2,
        MACIE_TLM_V_ASIC_5V,
        MACIE_TLM_V_FPGA_5V,
        MACIE_TLM_V_DVDD_3P3V,
        MACIE_TLM_V_DVDD_2P5V,
        MACIE_TLM_V_DVDD_1P8V,
        MACIE_TLM_V_DVDD_1P2V,
        MACIE_TLM_V_GIGE_3P3V,
        MACIE_TLM_V_USB_5V,
        MACIE_TLM_V_USB_3P3V,
        MACIE_TLM_V_VDDALOW1_ASIC,
        MACIE_TLM_V_VDDALOW2_ASIC,
        MACIE_TLM_V_SENSE_VDDAHIGH1,
        MACIE_TLM_V_SENSE_VDDAHIGH2,
        MACIE_TLM_V_SENSE_VDDALOW1,
        MACIE_TLM_V_SENSE_VDDALOW2,
        MACIE_TLM_V_SENSE_GNDA1,
        MACIE_TLM_V_SENSE_GNDA2,
        MACIE_TLM_V_VDDLOW1_ASIC,
        MACIE_TLM_V_VDDLOW2_ASIC,
        MACIE_TLM_V_SENSE_VDDHIGH1,
        MACIE_TLM_V_SENSE_VDDHIGH2,
        MACIE_TLM_V_SENSE_VDDLOW1,
        MACIE_TLM_V_SENSE_VDDLOW2,
        MACIE_TLM_V_SENSE_GND1,
        MACIE_TLM_V_SENSE_GND2,
        MACIE_TLM_V_VREF1_ASIC,
        MACIE_TLM_V_VREF2_ASIC,
        MACIE_TLM_V_AGND_CLEAN,
        MACIE_TLM_V_AGND_DIRTY,
        MACIE_TLM_V_DGND,
        MACIE_TLM_I_VDDAHIGH1,
        MACIE_TLM_I_VDDAHIGH2,
        MACIE_TLM_I_VDDALOW1,
        MACIE_TLM_I_VDDALOW2,
        MACIE_TLM_I_VREF1,
        MACIE_TLM_I_VREF2,
        MACIE_TLM_I_VDDHIGH1,
        MACIE_TLM_I_VDDHIGH2,
        MACIE_TLM_I_VDDLOW1,
        MACIE_TLM_I_VDDLOW2,
        MACIE_TLM_I_VDDIO1,
        MACIE_TLM_I_VDDIO2,
        MACIE_TLM_I_VSSIO1,
        MACIE_TLM_I_VSSIO2,
        MACIE_TLM_I_VDDAUX1,
        MACIE_TLM_I_VDDAUX2,
        MACIE_TLM_I_GNDA1,
        MACIE_TLM_I_GNDA2,
        MACIE_TLM_I_GND1,
        MACIE_TLM_I_GND2,
        MACIE_TLM_I_ASIC_5V,
        MACIE_TLM_I_FPGA_5V,
        MACIE_TLM_I_DVDD_3P3V,
        MACIE_TLM_I_DVDD_2P5V,
        MACIE_TLM_I_DVDD_1P8V,
        MACIE_TLM_I_DVDD_1P2V,
        MACIE_TLM_I_GIGE_3P3V,
        MACIE_TLM_I_USB_5V,
        MACIE_TLM_I_USB_3P3V
    } MACIE_TLM_ITEM;
    """
    TLM_V_VDDAHIGH1 = 0
    TLM_V_VDDAHIGH2 = 1
    TLM_V_VDDALOW1 = 2
    TLM_V_VDDALOW2 = 3
    TLM_V_VREF1 = 4
    TLM_V_VREF2 = 5
    TLM_V_VDDHIGH1 = 6
    TLM_V_VDDHIGH2 = 7
    TLM_V_VDDLOW1 = 8
    TLM_V_VDDLOW2 = 9
    TLM_V_VDDIO1 = 10
    TLM_V_VDDIO2 = 11
    TLM_V_VSSIO1 = 12
    TLM_V_VSSIO2 = 13
    TLM_V_VDDAUX1 = 14
    TLM_V_VDDAUX2 = 15
    TLM_V_GNDA1 = 16
    TLM_V_GNDA2 = 17
    TLM_V_GND1 = 18
    TLM_V_GND2 = 19
    TLM_V_ASIC_5V = 20
    TLM_V_FPGA_5V = 21
    TLM_V_DVDD_3P3V = 22
    TLM_V_DVDD_2P5V = 23
    TLM_V_DVDD_1P8V = 24
    TLM_V_DVDD_1P2V = 25
    TLM_V_GIGE_3P3V = 26
    TLM_V_USB_5V = 27
    TLM_V_USB_3P3V = 28
    TLM_V_VDDALOW1_ASIC = 29
    TLM_V_VDDALOW2_ASIC = 30
    TLM_V_SENSE_VDDAHIGH1 = 31
    TLM_V_SENSE_VDDAHIGH2 = 32
    TLM_V_SENSE_VDDALOW1 = 33
    TLM_V_SENSE_VDDALOW2 = 34
    TLM_V_SENSE_GNDA1 = 35
    TLM_V_SENSE_GNDA2 = 36
    TLM_V_VDDLOW1_ASIC = 37
    TLM_V_VDDLOW2_ASIC = 38
    TLM_V_SENSE_VDDHIGH1 = 39
    TLM_V_SENSE_VDDHIGH2 = 40
    TLM_V_SENSE_VDDLOW1 = 41
    TLM_V_SENSE_VDDLOW2 = 42
    TLM_V_SENSE_GND1 = 43
    TLM_V_SENSE_GND2 = 44
    TLM_V_VREF1_ASIC = 45
    TLM_V_VREF2_ASIC = 46
    TLM_V_AGND_CLEAN = 47
    TLM_V_AGND_DIRTY = 48
    TLM_V_DGND = 49
    TLM_I_VDDAHIGH1 = 50
    TLM_I_VDDAHIGH2 = 51
    TLM_I_VDDALOW1 = 52
    TLM_I_VDDALOW2 = 53
    TLM_I_VREF1 = 54
    TLM_I_VREF2 = 55
    TLM_I_VDDHIGH1 = 56
    TLM_I_VDDHIGH2 = 57
    TLM_I_VDDLOW1 = 58
    TLM_I_VDDLOW2 = 59
    TLM_I_VDDIO1 = 60
    TLM_I_VDDIO2 = 61
    TLM_I_VSSIO1 = 62
    TLM_I_VSSIO2 = 63
    TLM_I_VDDAUX1 = 64
    TLM_I_VDDAUX2 = 65
    TLM_I_GNDA1 = 66
    TLM_I_GNDA2 = 67
    TLM_I_GND1 = 68
    TLM_I_GND2 = 69
    TLM_I_ASIC_5V = 70
    TLM_I_FPGA_5V = 71
    TLM_I_DVDD_3P3V = 72
    TLM_I_DVDD_2P5V = 73
    TLM_I_DVDD_1P8V = 74
    TLM_I_DVDD_1P2V = 75
    TLM_I_GIGE_3P3V = 76
    TLM_I_USB_5V = 77
    TLM_I_USB_3P3V = 78


class CardInfo(ct.Structure):
    """
    macie.h
    -------
    typedef struct
    {
        unsigned short  macieSerialNumber;
        bool            bUART;
        bool            bGigE;
        bool            bUSB;
        unsigned char   ipAddr[4];
        unsigned short  gigeSpeed;
        char            serialPortName[10];
        char            usbSerialNumber[16];
        char            firmwareSlot1[100];
        char            firmwareSlot2[100];
        unsigned short  usbSpeed;
    } MACIE_CardInfo;
    """
    _fields_ = [
        ('macie_serial_number', ct.c_ushort),
        ('b_uart', ct.c_bool),
        ('b_gige', ct.c_bool),
        ('b_usb', ct.c_bool),
        ('ip_address', ct.c_ubyte*4),
        ('gige_speed', ct.c_ushort),
        ('serial_port_name', ct.c_char*10),
        ('usb_serial_number', ct.c_char*16),
        ('firmware_slot1', ct.c_char*100),
        ('firmware_slot2', ct.c_char*100),
        ('usb_speed', ct.c_ushort),
    ]


def card_to_dict(card):
    assert isinstance(card, CardInfo)
    _dict = {
        'macie_serial_number': card.macie_serial_number,
        'b_uart': card.b_uart,
        'b_gige': card.b_gige,
        'b_usb': card.b_usb,
        'ip_address': card.ip_address,
        'gige_speed': card.gige_speed,
        # 'serial_port_name': card.serial_port_name.decode('utf-8'),
        'usb_serial_number': card.usb_serial_number.decode('utf-8'),
        'firmware_slot1': card.firmware_slot1.decode('utf-8'),
        'firmware_slot2': card.firmware_slot2.decode('utf-8'),
        'usb_speed': card.usb_speed
    }
    _dict['ip_address'] = [_dict['ip_address'][i] for i in range(4)]
    try:
        _dict['serial_port_name'] = card.serial_port_name.decode('utf-8')
    except UnicodeDecodeError:
        _dict['serial_port_name'] = None
    return _dict


class FITSHeaderType(CtypesEnum):
    """
    macie.h
    -------
    typedef enum
    {
        HDR_INT,
        HDR_FLOAT,
        HDR_STR
    } Fits_HdrType;
    """
    HDR_INT = 0
    HDR_FLOAT = 1
    HDR_STR = 2


class FitsHeader(ct.Structure):
    """
    macie.h
    -------
    typedef struct
    {
        char key[9];
        Fits_HdrType valType;
        int   iVal;
        float fVal;
        char  sVal[72];
        char  comment[72];
    } MACIE_FitsHdr;
    """
    _fields_ = [
        ('key', ct.c_char * 9),
        ('val_type', ct.c_int),  # FITS_HDRTYPE
        ('i_val', ct.c_int),
        ('f_val', ct.c_float),
        ('s_val', ct.c_char * 72),
        ('comment', ct.c_char * 72),
    ]


class IpAddr(ct.Structure):
    """
    macie.h
    -------
    typedef struct
    {
        unsigned char   ipAddr[4];
    } MACIE_IpAddr;
    """
    _fields_ = [
        ('ip_address', ct.c_ubyte * 4)
    ]


def error():
    """
    Returns a text description of the last device error that occurred. When a MACIE function returns MACIE_FAIL,
     call this function for details regarding the type of failure.

    Returns
    -------
    error : str
        error message from MACIE software

    macie.h
    -------
    MACIESHARED_EXPORT char* MACIE_Error();
    """
    return "Made up simulation error message"


class MACIEBaseError(Exception):
    def __str__(self):
        return error()


class MACIEFailError(MACIEBaseError):
    pass


class ImageAcquisitionError(MACIEBaseError):
    pass


def handle_status(status):
    if status == Status.FAIL:
        raise MACIEFailError


def handle_image_array(image_array_pointer, frame_size):
    if image_array_pointer:
        array = np.ctypeslib.as_array(image_array_pointer, shape=(frame_size, ))
        print(array.shape[0], frame_size)
        return array
    else:
        raise ImageAcquisitionError


def lib_version():
    """
    This function returns the version number of the MACIE library. This function can be called at any time,
    even before MACIE_Init is called.

    Returns
    -------
    version : float
        version number of the MACIE library

    macie.h
    -------
    MACIESHARED_EXPORT float MACIE_LibVersion();
    """
    return 5.0


def init():
    """
    This is the starting point for the application to interface with the MACIE library. This function does not power up
     or initialize the MACIE hardware system. However, it must be called prior to using any other API function to
     communicate with the MACIE system, as it configured and prepares internal variables and structures that are needed
     by the other functions.

    To release any memory that is allocated by the MACIE_Init() function (e.g. before closing the user application),
     call the MACIE_Free() function.

    Returns
    -------
    None

    macie.h
    -------
    MACIESHARED_EXPORT MACIE_STATUS MACIE_Init();
    """
    pass


def free():
    """
    Free up all allocated resources including memory allocated with MACIE_Init().

    Returns
    -------
    None

    macie.h
    -------
    MACIESHARED_EXPORT MACIE_STATUS MACIE_Free();
    """
    pass


def check_interfaces(gige_command_port=0, ip_address_list=None):
    """
    Find all available MACIE cards that are connected to the computer (directly or via network) and provide information
    about the available interfaces (Camera Link, GigE and USB) to each card.

    Parameters
    ----------
    gige_command_port : int, optional
        Positive integer used for GigE port number. If 0, the default value 42306 will be used;
         otherwise the input value will be used. This port number has to match the port number configured in the
         MACIE Webserver for the TCP auto-connect selection (set to 42306 by default)
    ip_address_list : list, optional
        list of tuples containing the IPv4 addresses. e.g. [(192, 168, 1, 100), (192, 168, 1, 101)]
    Returns
    -------
    macie_card_info_pointer : list
        List of CardInfo objects containing information about all connected MACIE cards


    macie.h
    -------
    MACIESHARED_EXPORT MACIE_STATUS MACIE_CheckInterfaces( unsigned short gigeCommandPort,
                                                           MACIE_IpAddr *pIpAddrList,
                                                           unsigned short nIpAddr,
                                                           unsigned short *numCards,
                                                           MACIE_CardInfo **pCardInfo );
    """
    return [
        CardInfo(42, False, True, False, (192, 168, 121, 100), 1000, b'', b'', b'thebestfirmware', b'thebadfirmware', 0)
    ]


def set_gige_timeout(timeout):
    """
    Set a timeout for checking the GigE communication interface to any MACIE card on the network (when calling the
     MACIE_CheckInterfaces function). The default timeout of 200 ms will be applied if this function is not called.
     This timeout can be increased if the network is slow and the available MACIE cards cannot be reliably detected
     within the default timeout period.

    Parameters
    ----------
    timeout : int
        timeout in milliseconds for detecting GigE interface

    Returns
    -------
    None

    macie.h
    -------
    MACIESHARED_EXPORT MACIE_STATUS MACIE_SetGigeTimeout(unsigned short timeout);
    """
    pass


def get_handle(macie_serial_number, connection):
    """
    Set current communication interface with the input MACIE serial number and connection type. Then return a unique
     handle based on the input MACIE serial number and the Connection type.

    Parameters
    ----------
    macie_serial_number : int
        integer indicating the MACIE serial number
    connection : Connection
        enum value of MACIE_Connection

    Returns
    -------
    handle : int
        Nonzero indicates successful; zero means invalid MACIE serial number or connection

    macie.h
    -------
    MACIESHARED_EXPORT unsigned long MACIE_GetHandle( unsigned short MACIESerialNumber,
                                                      MACIE_Connection connection );
    """
    return randint(0, 2**16)


def get_available_macies(handle):
    """
    This function will report how many MACIE cards are connected through the same interface that is specified by the
     handle. Up to 8 MACIE cards can be plugged on top of each other through the board-to-board connectors, and can be
     accessed through a single interface to the computer.

    Parameters
    ----------
    handle : int
        integer obtained by get_handle function

    Returns
    -------
    A 8-bit unsigned integer with each bit indicating a MACIE card (up to 8 cards total). If 0 is returned, no MACIE
     card is available or the MACIE check failed. For example:
     0x03: means MACIE 0 and MACIE 1 are available.

    macie.h
    -------
    MACIESHARED_EXPORT unsigned char MACIE_GetAvailableASICs( unsigned long handle, int asicType );
    """
    return 3  # 00000011


def get_available_asics(handle, asic_type=0):
    """
    This function will report how many ASICs are connected through the same interface that is specified by the handle.
     Up to 8 ASICs can be connected, using up to 8 separate MACIE cards plugged on top of each other using the
     board-to-board connectors, and can be accessed through a single interface to the computer.

    Parameters
    ----------
    handle : int
        integer obtained by get_handle function
    asic_type : int, optional
        doesn't do anything, reserved for future use

    Returns
    -------
    A 8-bit unsigned integer with each bit indicating an ASIC (up to 8 ASICs total). If 0 is returned, no ASIC is
     available or the ASIC check failed. For example: 0x03: means ASIC 0 and ASIC 1 are available.

    macie.h
    -------
    MACIESHARED_EXPORT unsigned char MACIE_GetAvailableASICs( unsigned long handle, int asicType );
    """
    n_asics = 0
    for i in range(SETTINGS['NUMBEROFCAMERAS']):
        n_asics += 2 ** i
    return n_asics  # 00001101


def read_macie_register(handle, select_macies, address):
    """
    Read a MACIE register value.

    Parameters
    ----------
    handle : int
        integer obtained by get_handle function
    select_macies : byte
        selected MACIEs from MACIEs available in get_available_macies
    address : int
        register address you would like to read

    Returns
    -------
    value : int
        register value at given address

    macie.h
    -------
    MACIESHARED_EXPORT MACIE_STATUS MACIE_ReadMACIEReg( unsigned long  handle,
                                                        unsigned char  slctMACIEs,
                                                        unsigned short address,
                                                        unsigned int   *value );
    """
    return 0x8000


def write_macie_register(handle, select_macies, address, value):
    """
    Write value to MACIE register.

    Parameters
    ----------
    handle : int
        integer obtained by get_handle function
    select_macies : byte
        selected MACIEs from MACIEs available in get_available_macies
    address : int
        register address you would like to read
    value : int
        register value at given address

    Returns
    -------
    None

    macie.h
    -------
    MACIESHARED_EXPORT MACIE_STATUS MACIE_WriteMACIEReg( unsigned long  handle,
                                                         unsigned char  slctMACIEs,
                                                         unsigned short addrress,
                                                         unsigned int   value );
    """
    pass


def write_macie_block(handle, select_macies, starting_address, values):
    """
    Write a block of values to a contiguous set of MACIE registers.

    Parameters
    ----------
    handle : int
        integer obtained by get_handle function
    select_macies : byte
        selected MACIEs from MACIEs available in get_available_macies
    starting_address : int
        starting register address you would like to write
    values : list, tuple
        values to apply starting at the given address

    Returns
    -------
    None

    macie.h
    -------
    MACIESHARED_EXPORT MACIE_STATUS MACIE_WriteMACIEBlock( unsigned long  handle,
                                                           unsigned char  slctMACIEs,
                                                           unsigned short address,
                                                           unsigned int   *valueArray,
                                                           int            arrSize );
    """
    pass


def read_macie_block(handle, select_macies, starting_address, num_read_registers):
    """
    Read a number of registers starting at the specified register address.

    Parameters
    ----------
    handle : int
        integer obtained by get_handle function
    select_macies : byte
        selected MACIEs from MACIEs available in get_available_macies
    starting_address : int
        starting register address you would like to read
    num_read_registers : int
        number of consecutive registers to read

    Returns
    -------
    values : list
        list of register values with the first value corresponding to the starting_address given


    macie.h
    -------
    MACIESHARED_EXPORT MACIE_STATUS MACIE_ReadMACIEBlock( unsigned long  handle,
                                                      unsigned char  slctMACIEs,
                                                      unsigned short address,
                                                      unsigned int   *valueArray,
                                                      int            arrSize );
    """
    return [0x8000 for i in range(num_read_registers)]


def load_macie_firmware(handle, select_macies, firmware_slot=True):
    """
    Each MACIE card stores two FPGA firmware versions in the available on-board EEPROM slots (slot1 and slot2). Calling
     this function will load the firmware from the specified slot.

    Parameters
    ----------
    handle : int
        integer obtained by get_handle function
    select_macies : byte
        selected MACIEs from MACIEs available in get_available_macies
    firmware_slot : If true, load FPGA firmware from slot 1, otherwise load FPGA firmware from slot 2

    Returns
    -------
    firmware_result : int
        Integer indicating the value read from MACIE register 0xFFFB
        The following values are expected:
            base mode firmware: 0xBCDE
            SIDECAR firmware:   0xAC1E
            ACADIA firmware:    0xACDA

    macie.h
    -------
    MACIESHARED_EXPORT MACIE_STATUS MACIE_loadMACIEFirmware( unsigned long handle,
                                                             unsigned char slctMACIEs,
                                                             bool          bSlot1,
                                                             unsigned int  *pResult);
    """
    return 1


def download_macie_file(handle, select_macies, register_file):
    """
    Download a sequence of register settings from the MACIE register file (.mrf) to the MACIE card. This can be used to
     initialize the MACIE card and power up the ASIC power supplies, in addition to other desired configuration options.

    Parameters
    ----------
    handle : int
        integer obtained by get_handle function
    select_macies : byte
        selected MACIEs from MACIEs available in get_available_macies
    register_file : string, path
        MACIE register file .mrf

    Returns
    -------
    None

    macie.h
    -------
    MACIESHARED_EXPORT MACIE_STATUS MACIE_DownloadMACIEFile( unsigned long handle,
                                                             unsigned char slctMACIEs,
                                                             const char*   regFile );
    """
    pass


def get_acadia_address_increment(handle, select_macies):
    """
    Returns the current auto-increment configuration for mSPI read and write transactions to the ACADIA ASIC.

    Parameters
    ----------
    handle : int
        integer obtained by get_handle function
    select_macies : byte
        selected MACIEs from MACIEs available in get_available_macies

    Returns
    -------
    auto_address_increment : bool
        Boolean value indicating the auto address increment will be set or not. If true, the auto address increment will
         be set; if false, the auto address increment will be not set

    macie.h
    -------
    MACIESHARED_EXPORT MACIE_STATUS MACIE_GetAcadiaAddressIncrement( unsigned long handle,
                                                                     unsigned char  slctMACIEs,
                                                                     bool*       bAutoAddrInc);
    """
    return False


def set_acadia_address_increment(handle, select_macies, auto_address_increment):
    """
    Set or clear the auto-increment option for mSPI read and write transactions to the ACADIA ASIC.

    Parameters
    ----------
    handle : int
        integer obtained by get_handle function
    select_macies : byte
        selected MACIEs from MACIEs available in get_available_macies
    auto_address_increment : bool
        Boolean value indicating the auto address increment will be set or not. If true, the auto address increment will
         be set; if false, the auto address increment will be not set

    Returns
    -------
    None

    macie.h
    -------
    MACIESHARED_EXPORT MACIE_STATUS MACIE_SetAcadiaAddressIncrement( unsigned long handle,
                                                                     unsigned char  slctMACIEs,
                                                                     bool       bAutoAddrInc);
    """
    pass


def write_asic_register(handle, select_asics, address, value, b_option):
    """
    Write value to ASIC register.

    Parameters
    ----------
    handle : int
        integer obtained by get_handle function
    select_asics : byte
        selected ASICs from ASICs available in get_available_asics
    address : int
        register address you would like to read
    value : int
        register value at given address
    b_option : bool
        Boolean value indicating if DMA bit needs to be set (SIDECAR ASIC), or the mSPI-specific registers are to be
         addressed (ACADIA ASIC).

    Returns
    -------
    None

    macie.h
    -------
    MACIESHARED_EXPORT MACIE_STATUS MACIE_WriteASICReg( unsigned long  handle,
                                                        unsigned char  slctASICs,
                                                        unsigned short address,
                                                        unsigned int   value,
                                                        bool           bOption);
    """
    pass


def read_asic_register(handle, select_asics, address, b_24_bit, b_option):
    """
    Read ASIC register value

    Parameters
    ----------
    handle : int
        integer obtained by get_handle function
    select_asics : byte
        selected ASICs from ASICs available in get_available_asics
    address : int
        register address you would like to read
    b_24_bit : int
        Boolean value indicating readback of 24 bit instead of 16-bit. This parameter is only applicable when using the
         SIDECAR ASIC. For the ACADIA ASIC, this parameter is ignored.
    b_option : bool
        Boolean value indicating if DMA bit needs to be set (SIDECAR ASIC), or the mSPI-specific registers are to be
         addressed (ACADIA ASIC).

    Returns
    -------
    value : int
        register value at given address

    macie.h
    -------
    MACIESHARED_EXPORT MACIE_STATUS MACIE_ReadASICReg( unsigned long  handle,
                                                       unsigned char  slctASICs,
                                                       unsigned short address,
                                                       unsigned int   *value,
                                                       bool           b24bit,
                                                       bool           bOption );
    """
    return 0x8000


def write_asic_block(handle, select_asics, starting_address, values, b_option):
    """
    Write a number of contiguous ASIC registers starting at the specified register address.
    
    Parameters
    ----------
    handle : int
        integer obtained by get_handle function
    select_asics : byte
        selected ASICs from ASICs available in get_available_asics
    starting_address : int
        starting register address you would like to write
    values : list, tuple
        values to apply starting at the given address
    b_option : bool
        Boolean value indicating if DMA bit needs to be set (SIDECAR ASIC), or the mSPI-specific registers are to be
         addressed (ACADIA ASIC).

    Returns
    -------
    None

    macie.h
    -------
    MACIESHARED_EXPORT MACIE_STATUS MACIE_WriteASICBlock( unsigned long  handle,
                                                          unsigned char  slctASICs,
                                                          unsigned short address,
                                                          unsigned int   *valueArray,
                                                          int            arrSize,
                                                          bool           bOption );
    """
    pass


def read_asic_block(handle, select_asics, starting_address, num_read_registers, b_24_bit, b_option):
    """
    Read a number of contiguous ASIC registers starting at the specified register address.

    Parameters
    ----------
    handle : int
        integer obtained by get_handle function
    select_asics : byte
        selected ASICs from ASICs available in get_available_asics
    starting_address : int
        starting register address you would like to write
    num_read_registers : int
        number of consecutive registers to read
    b_24_bit : int
        Boolean value indicating readback of 24 bit instead of 16-bit. This parameter is only applicable when using the
         SIDECAR ASIC. For the ACADIA ASIC, this parameter is ignored.
    b_option : bool
        Boolean value indicating if DMA bit needs to be set (SIDECAR ASIC), or the mSPI-specific registers are to be
         addressed (ACADIA ASIC).

    Returns
    -------
    values : list, tuple
        values to apply starting at the given address

    macie.h
    -------
    MACIESHARED_EXPORT MACIE_STATUS  MACIE_ReadASICBlock( unsigned long  handle,
                                                          unsigned char  slctASICs,
                                                          unsigned short address,
                                                          unsigned int   *valueArray,
                                                          int            arrSize,
                                                          bool           b24bit,
                                                          bool           bOption );
    """
    return [0x8000 for i in range(num_read_registers)]


def download_asic_file(handle, select_asics, register_file, b_option):
    """
    Download a sequence of values to the ASIC from an ASIC configuration file (like .mcd for SIDECAR or .ald for ACADIA)

    Parameters
    ----------
    handle : int
        integer obtained by get_handle function
    select_asics : byte
        selected ASICs from ASICs available in get_available_asics
    register_file : string, path
        ASIC configuration file (like .mcd for SIDECAR or .ald for ACADIA)
    b_option : bool
        Boolean value indicating if DMA bit needs to be set (SIDECAR ASIC), or the mSPI-specific registers are to be
         addressed (ACADIA ASIC).

    Returns
    -------
    None

    macie.h
    -------
    MACIESHARED_EXPORT MACIE_STATUS MACIE_DownloadASICFile( unsigned long  handle,
                                                            unsigned char  slctASICs,
                                                            const char     *regFile,
                                                            bool           bOption );
    """
    pass


def close_port(handle):
    """
    Close the port corresponding to the provided handle.

    When writing to or reading from the MACIE card through any of the interfaces (GigE / USB / CameraLink UART), the
     corresponding port is automatically opened to facilitate the communication. Afterwards, the port is kept open until
     the user calls the MACIE_ClosePort function to close the port. Typically, closing the port is only required if the
     port needs to made available to other applications on the computer

    Parameters
    ----------
    handle : int
        integer obtained by get_handle function

    Returns
    -------
    None

    macie.h
    -------
    MACIESHARED_EXPORT MACIE_STATUS MACIE_ClosePort( unsigned long  handle );
    """
    pass


def reset_error_counters(handle, select_macies):
    """
    Reset all the MACIE error counters, including the MACIE and ASIC command error counters, timeout error counters and
     science interface error counters, etc.

    Parameters
    ----------
    handle : int
        integer obtained by get_handle function
    select_macies : byte
        selected MACIEs from MACIEs available in get_available_macies

    Returns
    -------
    None

    macie.h
    -------
    MACIESHARED_EXPORT MACIE_STATUS MACIE_ResetErrorCounters( unsigned long handle,
                                                              unsigned char slctMACIEs );
    """
    pass


def set_macie_phase_shift(handle, select_macies, clock_phase):
    """
    Optimize the ASIC clock phase for science data transmission from ASIC to MACIE. Normally is function is only used
     for ASIC fast mode application.

    Parameters
    ----------
    handle : int
        integer obtained by get_handle function
    select_macies : byte
        selected MACIEs from MACIEs available in get_available_macies
    clock_phase : byte
        Bit 7-0: set phase shift for the ASIC clock if bit 8 is set.
        Bit 8: enable ASIC phase shift, otherwise phase shift bits 7-0 are ignored

    Returns
    -------
    None

    macie.h
    -------
    MACIESHARED_EXPORT MACIE_STATUS MACIE_SetMACIEPhaseShift( unsigned long handle,
                                                              unsigned char slctMACIEs,
                                                              unsigned short clkPhase );
    """
    pass


def get_macie_phase_shift(handle, select_macies):
    """
    Get the current ASIC clock phase shift setting from the MACIE card.

    Parameters
    ----------
    handle : int
        integer obtained by get_handle function
    select_macies : byte
        selected MACIEs from MACIEs available in get_available_macies

    Returns
    -------
    clock_phase : byte
        Bit 7-0: set phase shift for the ASIC clock if bit 8 is set.
        Bit 8: enable ASIC phase shift, otherwise phase shift bits 7-0 are ignored

    macie.h
    -------
    MACIESHARED_EXPORT MACIE_STATUS MACIE_GetMACIEPhaseShift( unsigned long handle,
                                                              unsigned char slctMACIEs,
                                                              unsigned short *clkPhase );
    """
    return 10


def download_load_file(handle, select_macies, select_asics, register_file, b_option):
    """
    Download an individual register file or a master configuration file which includes a sequence of files to be loaded
     to the selected MACIEs and ASICs

    Parameters
    ----------
    handle : int
        integer obtained by get_handle function
    select_macies : byte
        selected MACIEs from MACIEs available in get_available_macies
    select_asics : byte
        selected ASICs from ASICs available in get_available_asics
    register_file : string, path
        Individual register file or a script file name. .glf or .mcf
    b_option : bool
        Boolean value indicating if DMA bit needs to be set (SIDECAR ASIC), or the mSPI-specific registers are to be
         addressed (ACADIA ASIC).

    Returns
    -------
    None

    macie.h
    -------
    MACIESHARED_EXPORT MACIE_STATUS MACIE_DownloadLoadfile( unsigned long  handle,
                                                            unsigned char  slctMACIEs,
                                                            unsigned char  slctASICs,
                                                            const char     *regFile,
                                                            bool           bOption );
    """
    pass


def get_error_counters(handle, select_macies):
    """
    Read MACIE error counter registers

    Parameters
    ----------
    handle : int
        integer obtained by get_handle function
    select_macies : byte
        selected MACIEs from MACIEs available in get_available_macies

    Returns
    -------
    error_counters

    macie.h
    -------
    MACIESHARED_EXPORT MACIE_STATUS MACIE_GetErrorCounters( unsigned long  handle,
                                                            unsigned char  slctMACIEs,
                                                            unsigned short *counterArray);
    """
    return 0


def configure_camlink_interface(handle, select_macies, mode, dcf_file, timeout, frame_x, frame_y):
    """
    Set up Camera Link interface for image acquisition.

    Note: This function is tied to using the Matrox Solios or Helios frame grabber with the MIL-lite library. If using
     other frame grabbers, the necessary MACIE setup has to be performed by the user using direct MACIE register writes
     to addresses 0x01c0 - 0x01c4.

    Parameters
    ----------
    handle : int
        integer obtained by get_handle function
    select_macies : byte
        selected MACIEs from MACIEs available in get_available_macies
    mode : int
        bit<4> Send Dummy Frames
        bit<6-5> Select dummy frame type:
            b00: all values are 0
            b01: incrementing value, starts at 0 at the beginning of each row b10: incrementing value, continues to
             increment at beginning of each row (instead of resetting to 0)
            b11: constant value per row, value increments with each row
    dcf_file : str, path
        Camera Link configuration file (.dcf)
    timeout : int
        time (in ms steps) after which the remainder of the Camera Link frame is filled with dummy 0s by MACIE card.
         If 0, the default timeout of 100 will be used
    frame_x : int
        Camera Link image size X
    frame_y : int
        Camera Link image size Y

    Returns
    -------
    buffer_size : int
        indicates the maximum number of images which can be stored in the non-paged memory allocated in the MIL Config

    macie.h
    -------
    MACIESHARED_EXPORT MACIE_STATUS MACIE_ConfigureCamLinkInterface( unsigned long handle,
                                                                     unsigned char slctMACIEs,
                                                                     unsigned short mode,
                                                                     const char    *dcfFFile,
                                                                     unsigned short timeout,
                                                                     unsigned short frameX,
                                                                     unsigned short frameY,
                                                                     short          *nBuffers );
    """
    return SETTINGS['FRAMEX'] * SETTINGS['FRAMEY'] * 16 * SETTINGS['NUMBEROFCAMERAS']


def configure_gige_science_interface(handle, select_macies, mode, frame_size, remote_port):
    """
    Set up GigE science data interface for image acquisition.

    Parameters
    ----------
    handle : int
        integer obtained by get_handle function
    select_macies : byte
        selected MACIEs from MACIEs available in get_available_macies
    mode : int
            bit <1-0> GigE_DataFormat:
                0 = 16-bit words
                1 = 24-bit words (e.g. 2*12bit)
                2 = 32-bit words
                3 = 32-bit words (2*12 bit aligned on word boundary)
            bit <6-4> Dummy Frame Type (auto-generates test science data):
                b000: Dummy test frames disabled (normal mode of operation)
                b001: fixed value of 0 for the whole frame
                b010: incrementing value, starts at 0 at the start of each row
                b011: incrementing value, continues to
                 increment at start of each row (instead of resetting to 0)
                b100: constant value per row, value increments with each row;
                b101: fixed value for the whole frame,
                 increments by 256 with each frame (512 for GigE_DataFormat 1 and 3)
                b110: incrementing value, starts over at the beginning of each row, increments by 256 with each frame
                 (512 for GigE_DataFormat 1 and 3)
                b111: incrementing value, continues to increment at beginning of each row, increments by 256 with each
                frame (512 for GigE_DataFormat 1 and 3)
    frame_size : int
        Integer indicating the image size of (frameX * frameY). When intending to read data using the
         MACIE_ReadGigeScienceData() function instead of the MACIE_ReadGigEScienceFrame() function, set this parameter
         to 0.
    remote_port : int
        integer indicating the GigE port number (e.g. 42037)
    Returns
    -------
    buffer_size : int
        integer indicating the available buffer size in the low level operating system buffer for the TCP socket
         connection [in KB].

    macie.h
    -------
    MACIESHARED_EXPORT MACIE_STATUS MACIE_ConfigureGigeScienceInterface( unsigned long handle,
                                                                         unsigned char slctMACIEs,
                                                                         unsigned short mode,
                                                                         int           frameSize,
                                                                         unsigned short remotePort,
                                                                         int            *bufSize );
    """
    return SETTINGS['FRAMEX'] * SETTINGS['FRAMEY'] * 16 * SETTINGS['NUMBEROFCAMERAS']


def configure_usb_science_interface(handle, select_macies, mode, frame_size, n_buffers):
    """
    Set up USB science data interface for image acquisition.

    Parameters
    ----------
    handle : int
        integer obtained by get_handle function
    select_macies : byte
        selected MACIEs from MACIEs available in get_available_macies
    mode : int
        bit <1-0> USB_DataFormat: 0 = 16-bit words
            1 = 24-bit words (e.g. 2*12bit)
            2 = 32-bit words
            3 = 32-bit words (2*12 bit aligned on word boundary)
        bit <6-4> Dummy Frame Type (auto-generates test science data):
            b000: Dummy test frames disabled (normal mode of operation) b001: fixed value of 0 for the whole frame
            b010: incrementing value, starts at 0 at the start of each row b011: incrementing value, continues to
             increment at start of each row (instead of resetting to 0)
            b100: constant value per row, value increments with each row; b101: fixed value for the whole frame,
             increments by 256 with each frame (512 for USB_DataFormat 1 and 3)
            b110: incrementing value, starts over at the beginning of each row, increments by 256 with each frame (512
             for USB_DataFormat 1 and 3)
            b111: incrementing value, continues to increment at beginning of each row, increments by 256 with each frame
            (512 for USB_DataFormat 1 and 3)
        bit <8> Dual Pipe Mode: Configures separate USB Pipe for science data instead of sharing the same Pipe with
         configuration read data. Enables parallel register read and science data acquisition, at the cost of reduced
         bandwidth. Requires to configure the USB control chip accordingly, which will be taken care of when using the
         corresponding MACIE library function.
    frame_size : int
        Integer indicating the image size or internal buffer size in number of data words. When intending to read data
         using MACIE_ReadUSBScienceData() instead of MACIE_ReadUSBScienceFrame(), this parameter only indicates the
         buffer size.

    n_buffers : int
        Number of image buffers allocated to receive science data

    Returns
    -------
    None

    macie.h
    -------
    MACIESHARED_EXPORT MACIE_STATUS MACIE_ConfigureUSBScienceInterface( unsigned long handle,
                                                                        unsigned char slctMACIEs,
                                                                        unsigned short mode,
                                                                        int           frameSize,
                                                                        short         nBuffers );
    """
    pass


def available_science_data(handle):
    """
    Return the number of science data bytes available on the specified interface port.

    Parameters
    ----------
    handle : int
        integer obtained by get_handle function

    Returns
    -------
    science_data_bytes : int
        number of science data bytes available on the specified interface port.
    macie.h
    -------
    MACIESHARED_EXPORT unsigned long MACIE_AvailableScienceData( unsigned long handle );
    """
    return SETTINGS['FRAMEX'] * SETTINGS['FRAMEY'] * 16 * SETTINGS['NUMBEROFCAMERAS']


def available_science_frames(handle):
    """
    Return the number of frames available on the specified interface port.

    Parameters
    ----------
    handle : int
        integer obtained by get_handle function

    Returns
    -------
    science_frames : int
        number of frames available on the port
    macie.h
    -------
    MACIESHARED_EXPORT unsigned long MACIE_AvailableScienceFrames( unsigned long handle );
    """
    return 1


def read_gige_science_frame(handle, timeout, frame_size):
    """
    Read image from the specified interface port

    Parameters
    ----------
    handle : int
        integer obtained by get_handle function
    timeout : int
        time (in ms) after which the function will stop reading from the port
    frame_size : int
        Integer indicating the image size or internal buffer size in number of data words.

    Returns
    -------
    image_array: list
        returns a frame-sized array of unsigned short image data

    macie.h
    -------
    MACIESHARED_EXPORT unsigned short* MACIE_ReadGigeScienceFrame( unsigned long handle,
                                                                   unsigned short timeout );
    """
    start_time = dt.now()
    n_asics = SETTINGS['NUMBEROFCAMERAS']
    frame_size = SETTINGS['FRAMEX'] * SETTINGS['FRAMEY']
    science_read_block_size = SETTINGS['FRAMEX']
    blocks_per_frame = int(frame_size / science_read_block_size)
    total_data_blocks = blocks_per_frame * n_asics
    total_frame_size = frame_size * n_asics
    all_indices = np.arange(total_frame_size).reshape(total_data_blocks, science_read_block_size)
    index_matcher = np.arange(total_data_blocks) % n_asics
    deinterleaving_array = np.asarray(
        [[np.ones(SETTINGS['FRAMEX'])*i for i in range(SETTINGS['NUMBEROFCAMERAS'])] for j in range(SETTINGS['FRAMEY'])]
    ).astype(np.uint16)
    end_time = dt.now()
    while (end_time - start_time).total_seconds() < SETTINGS['FRAMETIMESEC']:
        end_time = dt.now()
    return deinterleaving_array.reshape(total_frame_size)


def read_usb_science_frame(handle, timeout, frame_size):
    """
    Read image from the specified interface port.

    Parameters
    ----------
    handle : int
        integer obtained by get_handle function
    timeout : int
        time (in ms) after which the function will stop reading from the port
    frame_size : int
        Integer indicating the image size or internal buffer size in number of data words.

    Returns
    -------
    image_array: list
        returns a frame-sized array of unsigned short image data

    macie.h
    -------
    MACIESHARED_EXPORT unsigned short* MACIE_ReadUSBScienceFrame( unsigned long handle,
                                                                  unsigned short timeout );
    """
    return read_gige_science_frame(handle, timeout, frame_size)


def read_camlink_science_frame(handle, timeout, frame_size, tif_file_name=''):
    """
    Read Camera Link image.

    Parameters
    ----------
    handle : int
        integer obtained by get_handle function
    timeout : int
        time (in ms) after which the function will stop reading from the port
    frame_size : int
        Integer indicating the image size or internal buffer size in number of data words.
    tif_file_name : str, path
        .tif file name which is used by the MIL library to save the image data to disk. If an empty string is provided,
         no .tif file will be saved to disk.
    Returns
    -------
    image_array: list
        returns a frame-sized array of unsigned short image data

    macie.h
    -------
    MACIESHARED_EXPORT unsigned short* MACIE_ReadCamlinkScienceFrame( unsigned long handle,
                                                                  const char *tifFileName,
                                                                  unsigned short timeout );
    """
    return read_gige_science_frame(handle, timeout, frame_size)


def write_fits_file(file_name, frame_x, frame_y, frame_data, headers):
    """

    Parameters
    ----------
    file_name : str, path
        fits file name
    frame_x : int,
        image size X
    frame_y : int
        image size Y
    frame_data : list, tuple
        1D image data array acquired via read_[comm_type]_science_frame function
    headers : list, tuple
        list of FitsHeader objects to be written to fits file

    Returns
    -------
    None

    macie.h
    -------
    MACIESHARED_EXPORT MACIE_STATUS MACIE_WriteFitsFile( char        *fileName,
                                                         unsigned short frameX,
                                                         unsigned short frameY,
                                                         unsigned short *pData,
                                                         unsigned short nHeaders,
                                                         MACIE_FitsHdr  *pHeaders );
    """
    pass


def read_gige_science_data(handle, timeout, n_science_words_read):
    """
    Read science data. This function can be used for capturing science data in a non-fixed frame size format
     (for example: when interleaving guide windows with full field data).

    Parameters
    ----------
    handle : int
        integer obtained by get_handle function
    timeout : int
        time (in ms) after which the function will stop reading from the port
    n_science_words_read : int
        Number of science data words to read

    Returns
    -------
    science_words : list
        list of ints corresponding to the science words

    macie.h
    -------
    MACIESHARED_EXPORT int MACIE_ReadGigeScienceData( unsigned long handle,
                                                      unsigned short timeout,
                                                      long           n,
                                                      unsigned short *pData );
    """
    return np.asarray([0x8000 for i in range(n_science_words_read)])


def read_usb_science_data(handle, timeout, n_science_words_read):
    """
    Read science data. This function can be used for capturing science data in a non-fixed frame size format
     (for example: when interleaving guide windows with full field data).

    Parameters
    ----------
    handle : int
        integer obtained by get_handle function
    timeout : int
        time (in ms) after which the function will stop reading from the port
    n_science_words_read : int
        Number of science data words to read

    Returns
    -------
    science_words : list
        list of ints corresponding to the science words

    macie.h
    -------
    MACIESHARED_EXPORT int MACIE_ReadUSBScienceData(  unsigned long handle,
                                                  unsigned short timeout,
                                                  long           n,
                                                  unsigned short *pData );
    """
    return read_gige_science_data(handle, timeout, n_science_words_read)


def close_camlink_science_interface(handle, select_macies):
    """
    Close Solios frame grabber card and disable MACIE Camera Link Science interface.

    Parameters
    ----------
    handle : int
        integer obtained by get_handle function
    select_macies : byte
        selected MACIEs from MACIEs available in get_available_macies

    Returns
    -------
    None

    macie.h
    -------
    MACIESHARED_EXPORT MACIE_STATUS MACIE_CloseCamlinkScienceInterface( unsigned long handle,
                                                                        unsigned char slctMACIEs);
    """
    pass


def close_gige_science_interface(handle, select_macies):
    """
    Close MACIE GigE Science interface.

    Parameters
    ----------
    handle : int
        integer obtained by get_handle function
    select_macies : byte
        selected MACIEs from MACIEs available in get_available_macies

    Returns
    -------
    None

    macie.h
    -------
    MACIESHARED_EXPORT MACIE_STATUS MACIE_CloseGigeScienceInterface( unsigned long handle,
                                                                     unsigned char slctMACIEs);
    """
    pass


def close_usb_science_interface(handle, select_macies):
    """
    Close MACIE USB Science interface.

    Parameters
    ----------
    handle : int
        integer obtained by get_handle function
    select_macies : byte
        selected MACIEs from MACIEs available in get_available_macies

    Returns
    -------
    None

    macie.h
    -------
    MACIESHARED_EXPORT MACIE_STATUS MACIE_CloseUSBScienceInterface( unsigned long handle,
                                                                    unsigned char slctMACIEs);
    """
    pass


def set_voltage(handle, select_macies, power_id, power_value):
    """
    Set voltage (V) or current (mA) to the power supply item listed in the PowerDAC

    Parameters
    ----------
    handle : int
        integer obtained by get_handle function
    select_macies : byte
        selected MACIEs from MACIEs available in get_available_macies
    power_id : PowerDAC
        Power item of PowerDAC enum
    power_value : float
        floating number indicating voltage in the unit of V and the current in unit of mA

    Returns
    -------
    None

    macie.h
    -------
    MACIESHARED_EXPORT MACIE_STATUS MACIE_SetVoltage( unsigned long handle,
                                                      unsigned char slctMACIEs,
                                                      MACIE_PWR_DAC powerId,
                                                      float         powerValue);
    """
    pass


def get_voltage(handle, select_macies, power_id):
    """
    Get voltage (V) or current (mA) to the power supply item listed in the PowerDAC

    Parameters
    ----------
    handle : int
        integer obtained by get_handle function
    select_macies : byte
        selected MACIEs from MACIEs available in get_available_macies
    power_id : PowerDAC
        Power item of PowerDAC enum

    Returns
    -------
    power_value : float
        floating number indicating voltage in the unit of V and the current in unit of mA

    macie.h
    -------
    MACIESHARED_EXPORT MACIE_STATUS MACIE_GetVoltage( unsigned long handle,
                                                      unsigned char slctMACIEs,
                                                      MACIE_PWR_DAC powerId,
                                                      float*        powerValue);
    """
    return 0


def enable_power(handle, select_macies, power_control_ids):
    """
    Enable MACIE supply voltages using the power control items listed in PowerControl

    Parameters
    ----------
    handle : int
        integer obtained by get_handle function
    select_macies : byte
        selected MACIEs from MACIEs available in get_available_macies
    power_control_ids : list, tuple
        list of PowerControl items

    Returns
    -------
    None

    macie.h
    -------
    MACIESHARED_EXPORT MACIE_STATUS MACIE_EnablePower( unsigned long handle,
                                                       unsigned char  slctMACIEs,
                                                       MACIE_PWR_CTRL* pwrCtrlIdArr,
                                                       short          n);
    """
    pass

def disable_power(handle, select_macies, power_control_ids):
    """
    Disable MACIE supply voltages using the power control items listed in PowerControl

    Parameters
    ----------
    handle : int
        integer obtained by get_handle function
    select_macies : byte
        selected MACIEs from MACIEs available in get_available_macies
    power_control_ids : list, tuple
        list of PowerControl items

    Returns
    -------
    None

    macie.h
    -------
    MACIESHARED_EXPORT MACIE_STATUS MACIE_DisablePower( unsigned long handle,
                                                        unsigned char  slctMACIEs,
                                                        MACIE_PWR_CTRL* pwrCtrlIdArr,
                                                        short          n);
    """
    pass


def set_power(handle, select_macies, power_control_id, power_state):
    """
    Enable or disable a single power control item listed in the PowerControl

    Parameters
    ----------
    handle : int
        integer obtained by get_handle function
    select_macies : byte
        selected MACIEs from MACIEs available in get_available_macies
    power_control_id : int
        PowerControl item
    power_state : bool
        enable or disable the power control. If true, enable the power control, otherwise disable the power control

    Returns
    -------
    None

    macie.h
    -------
    MACIESHARED_EXPORT MACIE_STATUS MACIE_SetPower( unsigned long handle,
                                                    unsigned char  slctMACIEs,
                                                    MACIE_PWR_CTRL pwrCtrlId,
                                                    bool           bEnablePower);
    """
    pass


def get_power(handle, select_macies, power_control_id):
    """
    Get the power control status for the given power control item listed in PowerControl

    Parameters
    ----------
    handle : int
        integer obtained by get_handle function
    select_macies : byte
        selected MACIEs from MACIEs available in get_available_macies
    power_control_id : int
        PowerControl item

    Returns
    -------
    power_state : bool
        enable or disable the power control. If true, enable the power control, otherwise disable the power control

    macie.h
    -------
    MACIESHARED_EXPORT MACIE_STATUS MACIE_GetPower( unsigned long handle,
                                                    unsigned char  slctMACIEs,
                                                    MACIE_PWR_CTRL pwrCtrlId,
                                                    bool           bEnablePower);
    """
    return True


def set_telemetry_configuration(
        handle, select_macies, v_sample_rate, v_average, i_sample_rate, i_average, ground_reference
):
    """

    Parameters
    ----------
    handle : int
        integer obtained by get_handle function
    select_macies : byte
        selected MACIEs from MACIEs available in get_available_macies
    v_sample_rate : int
        Sample rate for voltage measurement, selectable from TLMSampleRate
    v_average : int
        Average parameter for voltage measurement, selectable from TLMAverage
    i_sample_rate : int
        Sample rate for current measurement, selectable from TLMSampleRate
    i_average : int
        Average parameter for current measurement, selectable from TLMAverage
    ground_reference : int
        Ground reference selected for the voltage / current measurement, selectable from TLMGroundReference

    Returns
    -------
    None

    macie.h
    -------
    MACIESHARED_EXPORT MACIE_STATUS MACIE_SetTelemetryConfiguration( unsigned long handle,
                                                                     unsigned char  slctMACIEs,
                                                                     MACIE_TLM_SAMPLE_RATE vSampleRate,
                                                                     MACIE_TLM_AVERAGE     vAverage,
                                                                     MACIE_TLM_SAMPLE_RATE iSampleRate,
                                                                     MACIE_TLM_AVERAGE     iAverage,
                                                                     MACIE_TLM_GROUND_REFERENCE groundRef);
    """
    pass


def get_telemetry_configuration(
        handle, select_macies
):
    """
    Get sample rate, average parameters and ground references used for telemetry measurement by MACIE card.

    Parameters
    ----------
    handle : int
        integer obtained by get_handle function
    select_macies : byte
        selected MACIEs from MACIEs available in get_available_macies

    Returns
    -------
    v_sample_rate : TLMSampleRate
        Sample rate for voltage measurement, selectable from TLMSampleRate
    v_average : TLMAverage
        Average parameter for voltage measurement, selectable from TLMAverage
    i_sample_rate : TLMSampleRate
        Sample rate for current measurement, selectable from TLMSampleRate
    i_average : TLMAverage
        Average parameter for current measurement, selectable from TLMAverage
    ground_reference : TLMGroundReference
        Ground reference selected for the voltage / current measurement, selectable from TLMGroundReference

    macie.h
    -------
    MACIESHARED_EXPORT MACIE_STATUS MACIE_GetTelemetryConfiguration( unsigned long handle,
                                                                     unsigned char  slctMACIEs,
                                                                     MACIE_TLM_SAMPLE_RATE* vSampleRate,
                                                                     MACIE_TLM_AVERAGE*     vAverage,
                                                                     MACIE_TLM_SAMPLE_RATE* iSampleRate,
                                                                     MACIE_TLM_AVERAGE*     iAverage,
                                                                     MACIE_TLM_GROUND_REFERENCE* groundRef);
     """
    return TLMSampleRate(0), TLMAverage(0), TLMSampleRate(0),\
        TLMAverage(0), TLMGroundReference(0)


def get_telemetry(handle, select_macies, tlm_id):
    """
    Get telemetry measurement performed by MACIE card for the given TLMItem

    Parameters
    ----------
    handle : int
        integer obtained by get_handle function
    select_macies : byte
        selected MACIEs from MACIEs available in get_available_macies
    tlm_id : TLMItem
        TLMItem for which you want a telemetry measurement
    Returns
    -------
    tlm_value : float
        floating number indicating the voltage measurement (V) or current measurement (mA)

    macie.h
    -------
    MACIESHARED_EXPORT MACIE_STATUS MACIE_GetTelemetry( unsigned long handle,
                                                        unsigned char  slctMACIEs,
                                                        MACIE_TLM_ITEM tlmId,
                                                        float*         tlmValue);
    """
    return 0x8000


def get_telemetry_set(handle, select_macies, tlm_ids):
    """
    Get a set of telemetry measurements performed by the MACIE card for the given array of telemetry items listed in
     TLMItem

    Parameters
    ----------
    handle : int
        integer obtained by get_handle function
    select_macies : byte
        selected MACIEs from MACIEs available in get_available_macies
    tlm_ids : list, tuple
        list of TLMItem for which you want telemetry measurements

    Returns
    -------
    tlm_values : list
        list of floating numbers indicating the voltage measurements (V) or current measurements (mA) corresponding to
         the given tlm_ids

    macie.h
    -------
    MACIESHARED_EXPORT MACIE_STATUS MACIE_GetTelemetrySet( unsigned long handle,
                                                           unsigned char  slctMACIEs,
                                                           MACIE_TLM_ITEM* tlmIdArr,
                                                           short           n,
                                                           float*         tlmValArr);
    """
    n_tlm_ids = len(tlm_ids)
    return [0x8000 for i in range(n_tlm_ids)]


def get_telemetry_all(handle, select_macies):
    """
    Get the full set of all telemetry measurements performed by the MACIE card for the given array of telemetry items
     listed in TLMItem

    Parameters
    ----------
    handle : int
        integer obtained by get_handle function
    select_macies : byte
        selected MACIEs from MACIEs available in get_available_macies

    Returns
    -------
    tlm_values : list
        list of floating numbers indicating the voltage measurements (V) or current measurements (mA)

    macie.h
    -------
    MACIESHARED_EXPORT MACIE_STATUS MACIE_GetTelemetryAll( unsigned long handle,
                                                           unsigned char  slctMACIEs,
                                                           float*       tlmValArr);
    """
    n_tlm_items = len(TLMItem)
    return [0x8000 for i in range(n_tlm_items)]
