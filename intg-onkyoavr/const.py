"""
Constants for Onkyo AVR integration.

:copyright: (c) 2025 by Quirin.
:license: Mozilla Public License Version 2.0, see LICENSE for more details.
"""

from enum import IntEnum

# =============================================================================
# Version
# =============================================================================
__version__ = "0.3.0"


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
# =============================================================================
SIMPLE_COMMANDS = [
    # Power
    "POWER_ON",
    "POWER_OFF",
    "POWER_TOGGLE",
    
    # Volume
    "VOLUME_UP",
    "VOLUME_DOWN",
    "MUTE_ON",
    "MUTE_OFF",
    "MUTE_TOGGLE",
    
    # Input Selection
    "INPUT_BD_DVD",
    "INPUT_CBL_SAT",
    "INPUT_GAME",
    "INPUT_AUX",
    "INPUT_PC",              # <-- HINZUGEFÜGT
    "INPUT_TV",
    "INPUT_STRM_BOX",
    "INPUT_CD",
    "INPUT_PHONO",
    "INPUT_TUNER",
    "INPUT_FM",
    "INPUT_AM",
    "INPUT_USB",
    "INPUT_NETWORK",
    "INPUT_BLUETOOTH",
    "INPUT_AIRPLAY",
    "INPUT_MUSIC_SERVER",
    "INPUT_INTERNET_RADIO",
    
    # Listening Modes
    "LISTENING_MODE_STEREO",
    "LISTENING_MODE_DIRECT",
    "LISTENING_MODE_SURROUND",
    "LISTENING_MODE_FILM",
    "LISTENING_MODE_MUSIC",
    "LISTENING_MODE_GAME",
    "LISTENING_MODE_THX",
    "LISTENING_MODE_ALL_CH_STEREO",
    "LISTENING_MODE_PURE_AUDIO",
    "LISTENING_MODE_AUTO",
    "LISTENING_MODE_UP",
    "LISTENING_MODE_DOWN",
    
    # Dimmer
    "DIMMER_BRIGHT",
    "DIMMER_DIM",
    "DIMMER_DARK",
    "DIMMER_OFF",
    "DIMMER_TOGGLE",
    
    # Display
    "DISPLAY_TOGGLE",
    
    # Late Night Mode
    "LATE_NIGHT_OFF",
    "LATE_NIGHT_LOW",
    "LATE_NIGHT_HIGH",
    "LATE_NIGHT_AUTO",
    
    # Audyssey
    "AUDYSSEY_OFF",
    "AUDYSSEY_MOVIE",
    "AUDYSSEY_MUSIC",
    "DYNAMIC_EQ_ON",
    "DYNAMIC_EQ_OFF",
    "DYNAMIC_VOLUME_OFF",
    "DYNAMIC_VOLUME_LIGHT",
    "DYNAMIC_VOLUME_MEDIUM",
    "DYNAMIC_VOLUME_HEAVY",
    
    # HDMI
    "HDMI_OUT_MAIN",
    "HDMI_OUT_SUB",
    "HDMI_OUT_BOTH",
    "HDMI_OUT_OFF",
    
    # OSD/Menu Navigation
    "MENU",
    "EXIT",
    "UP",
    "DOWN",
    "LEFT",
    "RIGHT",
    "ENTER",
    "RETURN",
    "HOME",
    "QUICK_SETUP",
    "AUDIO_INFO",
    "VIDEO_INFO",
    
    # Playback Control (for Network/USB)
    "PLAY",
    "PAUSE",
    "STOP",
    "PREVIOUS",
    "NEXT",
    "FAST_FORWARD",
    "REWIND",
    "REPEAT",
    "SHUFFLE",
    
    # Tuner
    "TUNER_PRESET_UP",
    "TUNER_PRESET_DOWN",
    "TUNER_FREQ_UP",
    "TUNER_FREQ_DOWN",
    "TUNER_MODE_FM",
    "TUNER_MODE_AM",
    
    # Zone 2
    "ZONE2_POWER_ON",
    "ZONE2_POWER_OFF",
    "ZONE2_VOLUME_UP",
    "ZONE2_VOLUME_DOWN",
    "ZONE2_MUTE_TOGGLE",
    
    # Misc
    "SLEEP_OFF",
    "SLEEP_30",
    "SLEEP_60",
    "SLEEP_90",
    "MEMORY_SETUP",
]


# =============================================================================
# Simple Command to eISCP mapping
# =============================================================================
SIMPLE_COMMAND_MAP = {
    # Power
    "POWER_ON": (CMD_POWER, "01"),
    "POWER_OFF": (CMD_POWER, "00"),
    "POWER_TOGGLE": (CMD_POWER, "QSTN"),  # Query triggers toggle behavior
    
    # Volume
    "VOLUME_UP": (CMD_VOLUME, "UP"),
    "VOLUME_DOWN": (CMD_VOLUME, "DOWN"),
    "MUTE_ON": (CMD_MUTE, "01"),
    "MUTE_OFF": (CMD_MUTE, "00"),
    "MUTE_TOGGLE": (CMD_MUTE, "TG"),
    
    # Input Selection
    "INPUT_BD_DVD": (CMD_INPUT, "10"),
    "INPUT_CBL_SAT": (CMD_INPUT, "01"),
    "INPUT_GAME": (CMD_INPUT, "02"),
    "INPUT_AUX": (CMD_INPUT, "03"),
    "INPUT_PC": (CMD_INPUT, "05"),       # <-- HINZUGEFÜGT
    "INPUT_TV": (CMD_INPUT, "12"),
    "INPUT_STRM_BOX": (CMD_INPUT, "11"),
    "INPUT_CD": (CMD_INPUT, "23"),
    "INPUT_PHONO": (CMD_INPUT, "22"),
    "INPUT_TUNER": (CMD_INPUT, "26"),
    "INPUT_FM": (CMD_INPUT, "24"),
    "INPUT_AM": (CMD_INPUT, "25"),
    "INPUT_USB": (CMD_INPUT, "29"),
    "INPUT_NETWORK": (CMD_INPUT, "2B"),
    "INPUT_BLUETOOTH": (CMD_INPUT, "2D"),
    "INPUT_AIRPLAY": (CMD_INPUT, "2E"),
    "INPUT_MUSIC_SERVER": (CMD_INPUT, "27"),
    "INPUT_INTERNET_RADIO": (CMD_INPUT, "28"),
    
    # Listening Modes
    "LISTENING_MODE_STEREO": (CMD_LISTENING_MODE, "00"),
    "LISTENING_MODE_DIRECT": (CMD_LISTENING_MODE, "01"),
    "LISTENING_MODE_SURROUND": (CMD_LISTENING_MODE, "02"),
    "LISTENING_MODE_FILM": (CMD_LISTENING_MODE, "03"),
    "LISTENING_MODE_MUSIC": (CMD_LISTENING_MODE, "06"),
    "LISTENING_MODE_GAME": (CMD_LISTENING_MODE, "05"),
    "LISTENING_MODE_THX": (CMD_LISTENING_MODE, "04"),
    "LISTENING_MODE_ALL_CH_STEREO": (CMD_LISTENING_MODE, "0C"),
    "LISTENING_MODE_PURE_AUDIO": (CMD_LISTENING_MODE, "11"),
    "LISTENING_MODE_AUTO": (CMD_LISTENING_MODE, "FF"),
    "LISTENING_MODE_UP": (CMD_LISTENING_MODE, "UP"),
    "LISTENING_MODE_DOWN": (CMD_LISTENING_MODE, "DOWN"),
    
    # Dimmer
    "DIMMER_BRIGHT": (CMD_DIMMER, "00"),
    "DIMMER_DIM": (CMD_DIMMER, "01"),
    "DIMMER_DARK": (CMD_DIMMER, "02"),
    "DIMMER_OFF": (CMD_DIMMER, "03"),
    "DIMMER_TOGGLE": (CMD_DIMMER, "DIM"),
    
    # Display
    "DISPLAY_TOGGLE": (CMD_DISPLAY, "TG"),
    
    # Late Night Mode
    "LATE_NIGHT_OFF": (CMD_LATE_NIGHT, "00"),
    "LATE_NIGHT_LOW": (CMD_LATE_NIGHT, "01"),
    "LATE_NIGHT_HIGH": (CMD_LATE_NIGHT, "02"),
    "LATE_NIGHT_AUTO": (CMD_LATE_NIGHT, "03"),
    
    # Audyssey
    "AUDYSSEY_OFF": (CMD_AUDYSSEY, "00"),
    "AUDYSSEY_MOVIE": (CMD_AUDYSSEY, "01"),
    "AUDYSSEY_MUSIC": (CMD_AUDYSSEY, "02"),
    "DYNAMIC_EQ_ON": (CMD_AUDYSSEY_EQ, "01"),
    "DYNAMIC_EQ_OFF": (CMD_AUDYSSEY_EQ, "00"),
    "DYNAMIC_VOLUME_OFF": (CMD_AUDYSSEY_VOL, "00"),
    "DYNAMIC_VOLUME_LIGHT": (CMD_AUDYSSEY_VOL, "01"),
    "DYNAMIC_VOLUME_MEDIUM": (CMD_AUDYSSEY_VOL, "02"),
    "DYNAMIC_VOLUME_HEAVY": (CMD_AUDYSSEY_VOL, "03"),
    
    # HDMI Output
    "HDMI_OUT_MAIN": (CMD_HDMI_OUTPUT, "01"),
    "HDMI_OUT_SUB": (CMD_HDMI_OUTPUT, "02"),
    "HDMI_OUT_BOTH": (CMD_HDMI_OUTPUT, "03"),
    "HDMI_OUT_OFF": (CMD_HDMI_OUTPUT, "00"),
    
    # OSD/Menu Navigation
    "MENU": (CMD_OSD_MENU, "MENU"),
    "EXIT": (CMD_OSD_MENU, "EXIT"),
    "UP": (CMD_OSD_MENU, "UP"),
    "DOWN": (CMD_OSD_MENU, "DOWN"),
    "LEFT": (CMD_OSD_MENU, "LEFT"),
    "RIGHT": (CMD_OSD_MENU, "RIGHT"),
    "ENTER": (CMD_OSD_MENU, "ENTER"),
    "RETURN": (CMD_OSD_MENU, "RETURN"),
    "HOME": (CMD_OSD_MENU, "HOME"),
    "QUICK_SETUP": (CMD_OSD_MENU, "QUICK"),
    "AUDIO_INFO": (CMD_AUDIO_INFO, "QSTN"),
    "VIDEO_INFO": (CMD_VIDEO_INFO, "QSTN"),
    
    # Playback Control
    "PLAY": (CMD_NET_USB_PLAY, "PLAY"),
    "PAUSE": (CMD_NET_USB_PLAY, "PAUSE"),
    "STOP": (CMD_NET_USB_PLAY, "STOP"),
    "PREVIOUS": (CMD_NET_USB_PLAY, "TRDN"),
    "NEXT": (CMD_NET_USB_PLAY, "TRUP"),
    "FAST_FORWARD": (CMD_NET_USB_PLAY, "FF"),
    "REWIND": (CMD_NET_USB_PLAY, "REW"),
    "REPEAT": (CMD_NET_USB_PLAY, "REPEAT"),
    "SHUFFLE": (CMD_NET_USB_PLAY, "RANDOM"),
    
    # Tuner
    "TUNER_PRESET_UP": (CMD_TUNER_PRESET, "UP"),
    "TUNER_PRESET_DOWN": (CMD_TUNER_PRESET, "DOWN"),
    "TUNER_FREQ_UP": (CMD_TUNER_FREQ, "UP"),
    "TUNER_FREQ_DOWN": (CMD_TUNER_FREQ, "DOWN"),
    "TUNER_MODE_FM": (CMD_TUNER_MODE, "00"),
    "TUNER_MODE_AM": (CMD_TUNER_MODE, "01"),
    
    # Zone 2
    "ZONE2_POWER_ON": (CMD_ZONE2_POWER, "01"),
    "ZONE2_POWER_OFF": (CMD_ZONE2_POWER, "00"),
    "ZONE2_VOLUME_UP": (CMD_ZONE2_VOLUME, "UP"),
    "ZONE2_VOLUME_DOWN": (CMD_ZONE2_VOLUME, "DOWN"),
    "ZONE2_MUTE_TOGGLE": (CMD_ZONE2_MUTE, "TG"),
    
    # Sleep Timer
    "SLEEP_OFF": (CMD_SLEEP, "OFF"),
    "SLEEP_30": (CMD_SLEEP, "1E"),  # 30 in hex
    "SLEEP_60": (CMD_SLEEP, "3C"),  # 60 in hex
    "SLEEP_90": (CMD_SLEEP, "5A"),  # 90 in hex
    
    # Memory
    "MEMORY_SETUP": (CMD_MEMORY, "STR"),
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
]