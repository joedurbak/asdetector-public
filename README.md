# Astrophysics Science Detector
[![DOI](https://zenodo.org/badge/838616917.svg)](https://zenodo.org/doi/10.5281/zenodo.13234065)

The Astrophysics Science Detector package (asdetector) provides a command line and tcp server interface to MACIE/ASIC detector readout systems.

This is an ITAR insensitive version, with ACADIA specific information removed. If you are using ACADIAs, and are not subject to ITAR restrictions, reach out to the author for a version that is closer to off the shelf functionality.

## Installation

1) Install underlying API software, [MACIE library](https://www.markury-scientific.com/).

   a) Add MACIE.dll or libMACIE.so to path

   b) If you are using MACIE with GigE, make sure python is allowed through the firewall to detect and communicate with the MACIE board

2) If not installed already, install python. I recommend [miniconda](https://docs.conda.io/en/latest/miniconda.html)
   1) If you are using a Windows computer, it is best to use this [installer](installers/Miniconda3-latest-Windows-x86_64.exe), and selecting the install option to add python to $PATH. This is especially convenient if you are using asdetector alongside the LabVIEW camera control software.
3) Install the required packages

    a) If you are using conda:
        
       $ conda install six astropy numpy matplotlib pandas
        
    b) If you are using pip:
        
       $ pip install six astropy numpy matplotlib pandas
4) Clone the repository:

       $ git clone https://github.com/joedurbak/asdetector-public
    
   1) If you are using asdetector alongside the LabVIEW camera control software it is best to clone this repository within `C:\PycharmProjects`. The path within the LabVIEW software can be changed, but this is the default location.

5) Configure [settings](#settings) if you want to change default settings.

6) Run the interface

       $ python detectorio.py --help

## Usage
    
    $ python detectorio.py COMMAND ARG1

Available commands, are:
* [SERVER](#server)
* [OPEN](#open)
* [INIT](#init)
* [START](#start)
* [CLOSE](#close)
* [STATUS](#status)
* [MODE](#mode)

**Note:** Commands are not case-sensitive

### SERVER

    $ python detectorio.py SERVER
    
The SERVER command creates a TCP/IP server that accepts the other commands in the same format as the command line interface

Available TCP/IP server commands are the same as the command line commands: OPEN, INIT, START, CLOSE

#### TCP Communication Protocol

Messages are expected to take the following form

    0xbeef[message_length_bytes (4 bytes)][message]

When a command completes, there will be an ETX message

    0xbeef[1][ETX]
    
    # in python byte string format:
    
    b'\xbe\xef\x00\x00\x00\x01\x03'

#### TCP Client

A simple client is available as well. It will send any message given as the argument.

    $ python server_client.py MESSAGE

Where "MESSAGE" is any message you would like to send. Preferably one of the available commands (OPEN, INIT, START, or CLOSE).

### OPEN

    $ python detectorio.py OPEN

Starts underlying detector API software. This command should be run at startup.

### INIT

    $ python detectorio.py INIT
    
Initializes hardware clocks and biases. Run this command 

### START

    $ python detectorio.py START [exposure_time] [skip_time] [number_exposures]

Takes exposures for a given `exposure_time`, skips saving frames up the ramp for the `skip_time` duration, and duplicates this exposure `number_exposure` times.

### CLOSE

    $ python detectorio.py CLOSE 
    
Closes underlying detector API software

### STATUS

    $ python detectorio.py STATUS
    
Returns the JSON string contained in the JSON status file

### MODE

    $ python detectorio.py MODE [mode]
    
Changes the frame reduction mode used to convert multiple up the ramp frames from an exposure to a single frame.

Current modes available:

1) CDS (last_frame-first_frame)
2) SSR (last_frame)
3) Fowler2
4) Fowler4
5) Fowler8
6) Fowler16

#### JSON Status File

The JSON Status file, status/status.json, has the following format:

    {
      "CommandStartTime": "",
      "CurrentCommand": "",
      "CommandComplete": false,
      "CommandCompleteTime": "",
      "ExposureTimeRemaining": -9999.9,
      "TotalFrameCount": -9999,
      "ExposureFrames": {
        "CAMERA0": [],
        "CAMERA1": [],
        "CAMERA2": [],
        "CAMERA3": []
      },
      "IntermediateReducedFrames": {
        "CAMERA0": [],
        "CAMERA1": [],
        "CAMERA2": [],
        "CAMERA3": []
      },
      "FinalReducedFrame": {
        "CAMERA0": "",
        "CAMERA1": "",
        "CAMERA2": "",
        "CAMERA3": ""
      }
    }

### Field definitions

* _CommandStartTime_ - Time when command was made
* _CurrentCommand_ - Command being executed
* _CommandComplete_ - Flags whether a command has completed
* _CommandCompleteTime_ - Time command was completed. Blank until command is complete
* _ExposureTimeRemaining_ - Time remaining in current exposure. Particular to START command
* _TotalFrameCount_ - Total raw frames for an exposure. Particular to START command
* _ExposureFrames_ - Dictionary containing a list for each camera with the absolute paths to the raw fits files for an exposure in chronological order. Particular to START command
* _IntermediateReducedFrames_ - Dictionary containing a list for each camera with the absolute paths to the bias subtracted fits files for an exposure in chronological order. These lightly processed frames are typically more useful for an observer. Particular to START command
* _FinalReducedFrame_ - Dictionary containing single reduced frame an exposure for each camera. This appears at the end of an exposure, and is the file the observer will take home with them. Particular to START command


## TCP Client

This module comes with a TCP client if you want to interact with the TCP server started by the `python detectorio.py SERVER` command.

Usage:

    $ python server_client.py [COMMAND] [ARG1] [ARG2]

Example:

    $ python server_client.py START 300 0 0

## Settings

Detector Readout settings should appear in the main folder in a file called settings.json. To obtain a template run: `python detectorio.py MODE CDS` and settings.json will appear in the git repo's base directory.

If a key is missing in the settings.json file, or if there is no settings.json file, the default will be used.

### Default settings dictionary

Here are the Python default settings. To obtain a json copy run: `python detectorio.py MODE CDS` and settings.json will appear in the git repo's base directory.

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

### FITSHEADER setting

The FITSHEADER setting expects a dictionary where the key is the header key is the keyword name and the value is another
dictionary with 2 keys, 'value' and 'comment'.

#### Example FITSHEADER

##### JSON element

    "FITSHEADER": {
       "SATURATE": {
         "value": 65535,
         "comment": "[ADU] detector saturation value"
       },
       "GAIN": {
         "value": 2.0,
         "comment": "[e-/ADU] gain value for detector"
       }
    }

##### Fits header output

    SATURATE=                65535 / [ADU] detector saturation value           
    GAIN0   =                  2.0 / [e-/ADU] gain value for detector        

## Log files

Date stamped log files can be found in the 'logs' directory. Messages are appended to the log with the following format:

    [UTC time stamp]\t[Logged message]\n\n\n
