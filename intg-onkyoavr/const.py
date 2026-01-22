"""
Constants for Onkyo AVR integration.

:copyright: (c) 2025 by Quirin.
:license: Mozilla Public License Version 2.0, see LICENSE for more details.
"""

from enum import IntEnum

# =============================================================================
# Version
# =============================================================================
__version__ = "0.3.1"


# =============================================================================
# Internal Events
# =============================================================================
class Events(IntEnum):
    """Internal driver events."""
    CONNECTED = 0
    DISCONNECTED = 1
    ERROR = 2
    UPDATE = 3
    IP_ADDRESS_CHANGED = 4


# =============================================================================
# AVR States
# =============================================================================
class States:
    """AVR states."""
    ON = "ON"
    OFF = "OFF"
    PLAYING = "PLAYING"
    PAUSED = "PAUSED"
    UNKNOWN = "UNKNOWN"
    UNAVAILABLE = "UNAVAILABLE"


# =============================================================================
# eISCP Command Codes
# =============================================================================

# Main Zone Commands
CMD_POWER = "PWR"           # System Power
CMD_VOLUME = "MVL"          # Master Volume
CMD_MUTE = "AMT"            # Audio Muting
CMD_INPUT = "SLI"           # Input Selector
CMD_LISTENING_MODE = "LMD"  # Listening Mode
CMD_LATE_NIGHT = "LTN"      # Late Night Mode
CMD_AUDYSSEY = "ADY"        # Audyssey
CMD_AUDYSSEY_EQ = "ADQ"     # Audyssey Dynamic EQ
CMD_AUDYSSEY_VOL = "ADV"    # Audyssey Dynamic Volume
CMD_RE_EQ = "RAS"           # Re-EQ / Academy Filter
CMD_TONE_BASS = "TFR"       # Tone Front Bass (was TFR)
CMD_TONE_TREBLE = "TFT"     # Tone Front Treble
CMD_SLEEP = "SLP"           # Sleep Timer
CMD_DISPLAY = "DIF"         # Display Mode
CMD_DIMMER = "DIM"          # Dimmer Level
CMD_HDMI_OUTPUT = "HDO"     # HDMI Output Selector
CMD_HDMI_AUDIO = "HAO"      # HDMI Audio Output
CMD_VIDEO_WIDE = "VWM"      # Video Wide Mode
CMD_VIDEO_RESOLUTION = "RES" # Video Resolution

# Audio Information
CMD_AUDIO_INFO = "IFA"      # Audio Information
CMD_VIDEO_INFO = "IFV"      # Video Information

# Speaker Commands
CMD_SPEAKER_A = "SPA"       # Speaker A
CMD_SPEAKER_B = "SPB"       # Speaker B
CMD_SPEAKER_LEVEL = "SPL"   # Speaker Level Calibration

# Tuner Commands
CMD_TUNER_FREQ = "TUN"      # Tuner Frequency
CMD_TUNER_PRESET = "PRS"    # Tuner Preset
CMD_TUNER_MODE = "TUM"      # Tuner Mode (AM/FM)

# Network/USB Commands
CMD_NET_USB_TITLE = "NTI"   # NET/USB Title Name
CMD_NET_USB_ARTIST = "NAT"  # NET/USB Artist Name
CMD_NET_USB_ALBUM = "NAL"   # NET/USB Album Name
CMD_NET_USB_TIME = "NTM"    # NET/USB Time Info
CMD_NET_USB_TRACK = "NTR"   # NET/USB Track Info
CMD_NET_USB_PLAY = "NTC"    # NET/USB Control (Play/Pause/Stop)
CMD_NET_USB_STATUS = "NST"  # NET/USB Play Status
CMD_NET_SERVICE = "NSV"     # NET Service
CMD_NET_KEYBOARD = "NKY"    # NET Keyboard

# OSD/Menu Commands
CMD_OSD_MENU = "OSD"        # OSD Menu
CMD_OSD_UP = "OSDUP"        # OSD Up
CMD_OSD_DOWN = "OSDDOWN"    # OSD Down
CMD_OSD_LEFT = "OSDLEFT"    # OSD Left
CMD_OSD_RIGHT = "OSDRIGHT"  # OSD Right
CMD_OSD_ENTER = "OSDENTER"  # OSD Enter
CMD_OSD_EXIT = "OSDEXIT"    # OSD Exit

# Zone 2 Commands
CMD_ZONE2_POWER = "ZPW"     # Zone 2 Power
CMD_ZONE2_VOLUME = "ZVL"    # Zone 2 Volume
CMD_ZONE2_MUTE = "ZMT"      # Zone 2 Mute
CMD_ZONE2_INPUT = "SLZ"     # Zone 2 Input Selector
CMD_ZONE2_TONE = "ZTN"      # Zone 2 Tone

# Zone 3 Commands
CMD_ZONE3_POWER = "PW3"     # Zone 3 Power
CMD_ZONE3_VOLUME = "VL3"    # Zone 3 Volume
CMD_ZONE3_MUTE = "MT3"      # Zone 3 Mute
CMD_ZONE3_INPUT = "SL3"     # Zone 3 Input Selector

# Memory/Preset Commands
CMD_MEMORY = "MEM"          # Memory Setup
CMD_PRESET = "NPR"          # NET Preset

# Misc Commands
CMD_FIRMWARE = "FWV"        # Firmware Version
CMD_DEVICE_MEMORY = "DMS"   # Device Memory Status


# =============================================================================
# Input Sources - Complete mapping for Onkyo receivers
# =============================================================================
INPUT_SOURCES = {
    # Standard Video/Audio Inputs (0x00-0x0F)
    "00": "VIDEO1",
    "01": "CBL/SAT",
    "02": "GAME",
    "03": "AUX",
    "04": "AUX2",
    "05": "PC",
    "06": "VIDEO6",
    "07": "VIDEO7",
    
    # BD/DVD and Streaming (0x10-0x1F)
    "10": "BD/DVD",
    "11": "STRM BOX",
    "12": "TV",
    "13": "TAPE1",
    "14": "TAPE2",
    "15": "VIDEO9",
    "16": "VIDEO10",
    
    # Audio Inputs (0x20-0x2F)
    "20": "PHONO",
    "21": "TV/CD",
    "22": "TUNER",
    "23": "CD",
    "24": "FM",
    "25": "AM",
    "26": "TUNER",
    "27": "MUSIC SERVER",
    "28": "INTERNET RADIO",
    "29": "USB FRONT",
    "2A": "USB REAR",
    "2B": "NETWORK",
    "2C": "USB TOGGLE",
    "2D": "BLUETOOTH",
    "2E": "AIRPLAY",
    "2F": "USB DAC",
    
    # Multi-channel and Special (0x30-0x3F)
    "30": "MULTI CH",
    "31": "XM",
    "32": "SIRIUS",
    "33": "DAB",
    "34": "WIDE FM",
    "35": "SOURCE",
    
    # Universal Port (0x40-0x4F)
    "40": "UNIVERSAL PORT",
    "41": "LINE",
    "42": "LINE2",
    
    # HDMI Inputs (0x50-0x5F) - for some models
    "50": "HDMI1",
    "51": "HDMI2",
    "52": "HDMI3",
    "53": "HDMI4",
    "54": "HDMI5",
    "55": "HDMI6",
    "56": "HDMI7",
    
    # Selector Position Names (0x80+)
    "80": "SOURCE",
}

# Reverse mapping: Name -> Code
SOURCE_TO_CODE = {v: k for k, v in INPUT_SOURCES.items()}


# =============================================================================
# Listening Modes
# =============================================================================
LISTENING_MODES = {
    "00": "STEREO",
    "01": "DIRECT",
    "02": "SURROUND",
    "03": "FILM",
    "04": "THX",
    "05": "ACTION",
    "06": "MUSICAL",
    "07": "MONO MOVIE",
    "08": "ORCHESTRA",
    "09": "UNPLUGGED",
    "0A": "STUDIO-MIX",
    "0B": "TV LOGIC",
    "0C": "ALL CH STEREO",
    "0D": "THEATER-DIMENSIONAL",
    "0E": "ENHANCED",
    "0F": "MONO",
    "11": "PURE AUDIO",
    "12": "MULTIPLEX",
    "13": "FULL MONO",
    "14": "DOLBY VIRTUAL",
    "15": "DTS SURROUND SENSATION",
    "16": "AUDYSSEY DSX",
    "1F": "WHOLE HOUSE",
    "23": "STAGE",
    "25": "ACTION",
    "26": "MUSIC",
    "2E": "SPORTS",
    "40": "STRAIGHT DECODE",
    "41": "DOLBY EX/DTS ES",
    "42": "THX CINEMA",
    "43": "THX SURROUND EX",
    "44": "THX MUSIC",
    "45": "THX GAMES",
    "50": "THX U2/S2 CINEMA",
    "51": "THX MUSICMODE",
    "52": "THX GAMES MODE",
    "80": "PLII/PLIIx MOVIE",
    "81": "PLII/PLIIx MUSIC",
    "82": "NEO:6 CINEMA",
    "83": "NEO:6 MUSIC",
    "84": "PLII/PLIIx THX CINEMA",
    "85": "NEO:6 THX CINEMA",
    "86": "PLII/PLIIx GAME",
    "87": "NEURAL SURROUND",
    "88": "NEURAL THX",
    "89": "PLII THX GAMES",
    "8A": "NEO:6 THX GAMES",
    "8B": "PLII/PLIIx THX MUSIC",
    "8C": "NEO:6 THX MUSIC",
    "8D": "NEURAL THX CINEMA",
    "8E": "NEURAL THX MUSIC",
    "8F": "NEURAL THX GAMES",
    "90": "PLIIz HEIGHT",
    "91": "NEO:6 CINEMA DTS SURROUND SENSATION",
    "92": "NEO:6 MUSIC DTS SURROUND SENSATION",
    "93": "NEURAL DIGITAL MUSIC",
    "94": "PLIIz HEIGHT THX CINEMA",
    "95": "PLIIz HEIGHT THX MUSIC",
    "96": "PLIIz HEIGHT THX GAMES",
    "97": "PLIIz HEIGHT THX U2/S2 CINEMA",
    "98": "PLIIz HEIGHT THX MUSICMODE",
    "99": "PLIIz HEIGHT THX GAMES MODE",
    "9A": "NEO:X CINEMA",
    "9B": "NEO:X MUSIC",
    "9C": "NEO:X GAME",
    "A0": "PLIIx/PLII MOVIE + AUDYSSEY DSX",
    "A1": "PLIIx/PLII MUSIC + AUDYSSEY DSX",
    "A2": "PLIIx/PLII GAME + AUDYSSEY DSX",
    "A3": "NEO:6 CINEMA + AUDYSSEY DSX",
    "A4": "NEO:6 MUSIC + AUDYSSEY DSX",
    "A5": "NEURAL SURROUND + AUDYSSEY DSX",
    "A6": "NEURAL DIGITAL MUSIC + AUDYSSEY DSX",
    "A7": "DOLBY EX + AUDYSSEY DSX",
    "FF": "AUTO SURROUND",
}

LISTENING_MODE_TO_CODE = {v: k for k, v in LISTENING_MODES.items()}


# =============================================================================
# Simple Commands for Remote Entity
# These can be used in macros and activities
# Short names for better UI display!
# =============================================================================
SIMPLE_COMMANDS = [
    # Power
    "Power On",
    "Power Off",
    "Power Toggle",
    
    # Volume
    "Vol +",
    "Vol -",
    "Mute On",
    "Mute Off",
    "Mute Toggle",
    
    # Input Selection
    "BD/DVD",
    "CBL/SAT",
    "Game",
    "AUX",
    "TV",
    "Strm Box",
    "CD",
    "Phono",
    "Tuner",
    "PC",
    "FM",
    "AM",
    "USB",
    "Network",
    "Bluetooth",
    "AirPlay",
    "Music Server",
    "Net Radio",
    
    # Listening Modes
    "Stereo",
    "Direct",
    "Surround",
    "Film",
    "Music",
    "Game Mode",
    "THX",
    "All Ch Stereo",
    "Pure Audio",
    "Auto Surround",
    "Mode +",
    "Mode -",
    
    # Dimmer
    "Dimmer Bright",
    "Dimmer Dim",
    "Dimmer Dark",
    "Dimmer Off",
    "Dimmer Toggle",
    
    # Display
    "Display Toggle",
    
    # Late Night Mode
    "Late Night Off",
    "Late Night Low",
    "Late Night High",
    "Late Night Auto",
    
    # Audyssey
    "Audyssey Off",
    "Audyssey Movie",
    "Audyssey Music",
    "Dyn EQ On",
    "Dyn EQ Off",
    "Dyn Vol Off",
    "Dyn Vol Light",
    "Dyn Vol Medium",
    "Dyn Vol Heavy",
    
    # HDMI
    "HDMI Main",
    "HDMI Sub",
    "HDMI Both",
    "HDMI Off",
    
    # OSD/Menu Navigation
    "Menu",
    "Exit",
    "Up",
    "Down",
    "Left",
    "Right",
    "Enter",
    "Return",
    "Home",
    "Quick Setup",
    "Audio Info",
    "Video Info",
    
    # Playback Control (for Network/USB)
    "Play",
    "Pause",
    "Stop",
    "Previous",
    "Next",
    "Fast Fwd",
    "Rewind",
    "Repeat",
    "Shuffle",
    
    # Tuner
    "Preset +",
    "Preset -",
    "Freq +",
    "Freq -",
    "FM Mode",
    "AM Mode",
    
    # Zone 2
    "Zone2 On",
    "Zone2 Off",
    "Zone2 Vol +",
    "Zone2 Vol -",
    "Zone2 Mute",
    
    # Misc
    "Sleep Off",
    "Sleep 30",
    "Sleep 60",
    "Sleep 90",
    "Memory",
]


# =============================================================================
# Simple Command to eISCP mapping
# =============================================================================
SIMPLE_COMMAND_MAP = {
    # Power
    "Power On": (CMD_POWER, "01"),
    "Power Off": (CMD_POWER, "00"),
    "Power Toggle": (CMD_POWER, "QSTN"),
    
    # Volume
    "Vol +": (CMD_VOLUME, "UP"),
    "Vol -": (CMD_VOLUME, "DOWN"),
    "Mute On": (CMD_MUTE, "01"),
    "Mute Off": (CMD_MUTE, "00"),
    "Mute Toggle": (CMD_MUTE, "TG"),
    
    # Input Selection
    "BD/DVD": (CMD_INPUT, "10"),
    "CBL/SAT": (CMD_INPUT, "01"),
    "Game": (CMD_INPUT, "02"),
    "AUX": (CMD_INPUT, "03"),
    "TV": (CMD_INPUT, "12"),
    "Strm Box": (CMD_INPUT, "11"),
    "CD": (CMD_INPUT, "23"),
    "Phono": (CMD_INPUT, "22"),
    "PC": (CMD_INPUT, "05"),
    "Tuner": (CMD_INPUT, "26"),
    "FM": (CMD_INPUT, "24"),
    "AM": (CMD_INPUT, "25"),
    "USB": (CMD_INPUT, "29"),
    "Network": (CMD_INPUT, "2B"),
    "Bluetooth": (CMD_INPUT, "2D"),
    "AirPlay": (CMD_INPUT, "2E"),
    "Music Server": (CMD_INPUT, "27"),
    "Net Radio": (CMD_INPUT, "28"),
    
    # Listening Modes
    "Stereo": (CMD_LISTENING_MODE, "00"),
    "Direct": (CMD_LISTENING_MODE, "01"),
    "Surround": (CMD_LISTENING_MODE, "02"),
    "Film": (CMD_LISTENING_MODE, "03"),
    "Music": (CMD_LISTENING_MODE, "06"),
    "Game Mode": (CMD_LISTENING_MODE, "05"),
    "THX": (CMD_LISTENING_MODE, "04"),
    "All Ch Stereo": (CMD_LISTENING_MODE, "0C"),
    "Pure Audio": (CMD_LISTENING_MODE, "11"),
    "Auto Surround": (CMD_LISTENING_MODE, "FF"),
    "Mode +": (CMD_LISTENING_MODE, "UP"),
    "Mode -": (CMD_LISTENING_MODE, "DOWN"),
    
    # Dimmer
    "Dimmer Bright": (CMD_DIMMER, "00"),
    "Dimmer Dim": (CMD_DIMMER, "01"),
    "Dimmer Dark": (CMD_DIMMER, "02"),
    "Dimmer Off": (CMD_DIMMER, "03"),
    "Dimmer Toggle": (CMD_DIMMER, "DIM"),
    
    # Display
    "Display Toggle": (CMD_DISPLAY, "TG"),
    
    # Late Night Mode
    "Late Night Off": (CMD_LATE_NIGHT, "00"),
    "Late Night Low": (CMD_LATE_NIGHT, "01"),
    "Late Night High": (CMD_LATE_NIGHT, "02"),
    "Late Night Auto": (CMD_LATE_NIGHT, "03"),
    
    # Audyssey
    "Audyssey Off": (CMD_AUDYSSEY, "00"),
    "Audyssey Movie": (CMD_AUDYSSEY, "01"),
    "Audyssey Music": (CMD_AUDYSSEY, "02"),
    "Dyn EQ On": (CMD_AUDYSSEY_EQ, "01"),
    "Dyn EQ Off": (CMD_AUDYSSEY_EQ, "00"),
    "Dyn Vol Off": (CMD_AUDYSSEY_VOL, "00"),
    "Dyn Vol Light": (CMD_AUDYSSEY_VOL, "01"),
    "Dyn Vol Medium": (CMD_AUDYSSEY_VOL, "02"),
    "Dyn Vol Heavy": (CMD_AUDYSSEY_VOL, "03"),
    
    # HDMI Output
    "HDMI Main": (CMD_HDMI_OUTPUT, "01"),
    "HDMI Sub": (CMD_HDMI_OUTPUT, "02"),
    "HDMI Both": (CMD_HDMI_OUTPUT, "03"),
    "HDMI Off": (CMD_HDMI_OUTPUT, "00"),
    
    # OSD/Menu Navigation
    "Menu": (CMD_OSD_MENU, "MENU"),
    "Exit": (CMD_OSD_MENU, "EXIT"),
    "Up": (CMD_OSD_MENU, "UP"),
    "Down": (CMD_OSD_MENU, "DOWN"),
    "Left": (CMD_OSD_MENU, "LEFT"),
    "Right": (CMD_OSD_MENU, "RIGHT"),
    "Enter": (CMD_OSD_MENU, "ENTER"),
    "Return": (CMD_OSD_MENU, "RETURN"),
    "Home": (CMD_OSD_MENU, "HOME"),
    "Quick Setup": (CMD_OSD_MENU, "QUICK"),
    "Audio Info": (CMD_AUDIO_INFO, "QSTN"),
    "Video Info": (CMD_VIDEO_INFO, "QSTN"),
    
    # Playback Control
    "Play": (CMD_NET_USB_PLAY, "PLAY"),
    "Pause": (CMD_NET_USB_PLAY, "PAUSE"),
    "Stop": (CMD_NET_USB_PLAY, "STOP"),
    "Previous": (CMD_NET_USB_PLAY, "TRDN"),
    "Next": (CMD_NET_USB_PLAY, "TRUP"),
    "Fast Fwd": (CMD_NET_USB_PLAY, "FF"),
    "Rewind": (CMD_NET_USB_PLAY, "REW"),
    "Repeat": (CMD_NET_USB_PLAY, "REPEAT"),
    "Shuffle": (CMD_NET_USB_PLAY, "RANDOM"),
    
    # Tuner
    "Preset +": (CMD_TUNER_PRESET, "UP"),
    "Preset -": (CMD_TUNER_PRESET, "DOWN"),
    "Freq +": (CMD_TUNER_FREQ, "UP"),
    "Freq -": (CMD_TUNER_FREQ, "DOWN"),
    "FM Mode": (CMD_TUNER_MODE, "00"),
    "AM Mode": (CMD_TUNER_MODE, "01"),
    
    # Zone 2
    "Zone2 On": (CMD_ZONE2_POWER, "01"),
    "Zone2 Off": (CMD_ZONE2_POWER, "00"),
    "Zone2 Vol +": (CMD_ZONE2_VOLUME, "UP"),
    "Zone2 Vol -": (CMD_ZONE2_VOLUME, "DOWN"),
    "Zone2 Mute": (CMD_ZONE2_MUTE, "TG"),
    
    # Sleep Timer
    "Sleep Off": (CMD_SLEEP, "OFF"),
    "Sleep 30": (CMD_SLEEP, "1E"),
    "Sleep 60": (CMD_SLEEP, "3C"),
    "Sleep 90": (CMD_SLEEP, "5A"),
    
    # Memory
    "Memory": (CMD_MEMORY, "STR"),
}


# =============================================================================
# Media Player Features for Remote Two
# =============================================================================
MEDIA_PLAYER_FEATURES = [
    "on_off",
    "toggle",
    "volume",
    "volume_up_down",
    "mute_toggle",
    "mute",
    "unmute",
    "play_pause",
    "stop",
    "next",
    "previous",
    "select_source",
    "select_sound_mode",
    "dpad",
    "menu",
    "context_menu",
    "info",
    "home",
