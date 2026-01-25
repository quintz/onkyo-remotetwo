"""
Constants for Onkyo AVR integration.

:copyright: (c) 2025 by Quirin.
:license: Mozilla Public License Version 2.0, see LICENSE for more details.
"""

from enum import IntEnum

# =============================================================================
# Version
# =============================================================================
__version__ = "0.4.1"


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
# Receiver Series - Simplified categorization based on eISCP modelsets
# =============================================================================
RECEIVER_SERIES = {
    "TX-NR5xx": {
        "name": "TX-NR5xx Serie",
        "label": "TX-NR5xx (z.B. NR555, NR575, NR579)",
        "description": "Onkyo TX-NR 500er Serie",
        "models": ["TX-NR555", "TX-NR575", "TX-NR575E", "TX-NR579"],
        "supported_sets": ["set1", "set2", "set3", "set4", "set6", "set7", "set11"],
    },
    "TX-NR6xx": {
        "name": "TX-NR6xx Serie",
        "label": "TX-NR6xx (z.B. NR616, NR656, NR676, NR696)",
        "description": "Onkyo TX-NR 600er Serie",
        "models": ["TX-NR609", "TX-NR616", "TX-NR626", "TX-NR636", "TX-NR646", "TX-NR656", "TX-NR676", "TX-NR686", "TX-NR696"],
        "supported_sets": ["set1", "set2", "set3", "set4", "set6", "set7", "set11"],
    },
    "TX-NR7xx": {
        "name": "TX-NR7xx Serie", 
        "label": "TX-NR7xx (z.B. NR717, NR747, NR777)",
        "description": "Onkyo TX-NR 700er Serie",
        "models": ["TX-NR708", "TX-NR709", "TX-NR717", "TX-NR727", "TX-NR737", "TX-NR747", "TX-NR757", "TX-NR777", "TX-NR787", "TX-NR797"],
        "supported_sets": ["set1", "set2", "set3", "set4", "set6", "set7", "set8", "set11"],
    },
    "TX-RZxxx": {
        "name": "TX-RZ Serie",
        "label": "TX-RZxxx (z.B. RZ610, RZ720, RZ810)",
        "description": "Onkyo TX-RZ Serie (High-End)",
        "models": ["TX-RZ610", "TX-RZ620", "TX-RZ710", "TX-RZ720", "TX-RZ800", "TX-RZ810", "TX-RZ820", "TX-RZ900", "TX-RZ1100", "TX-RZ3100"],
        "supported_sets": ["set1", "set2", "set3", "set6", "set7", "set8", "set9", "set11"],
    },
    "TX-NR8xx-9xx": {
        "name": "TX-NR8xx/9xx Serie",
        "label": "TX-NR8xx/9xx (z.B. NR818, NR929)",
        "description": "Onkyo TX-NR 800er/900er Serie",
        "models": ["TX-NR807", "TX-NR808", "TX-NR809", "TX-NR818", "TX-NR828", "TX-NR838", "TX-NR900", "TX-NR901", "TX-NR905", "TX-NR906", "TX-NR929"],
        "supported_sets": ["set1", "set3", "set7", "set8", "set9", "set11"],
    },
    "GENERIC": {
        "name": "Andere / Unbekannt",
        "label": "Andere Onkyo Receiver",
        "description": "Basis-Befehle für alle Onkyo Receiver",
        "models": [],
        "supported_sets": ["set1"],  # Nur Basis-Befehle
    },
}


def get_series_choices() -> list:
    """Get list of receiver series for setup dropdown."""
    return [
        {"id": series_id, "label": {"en": info["label"], "de": info["label"]}}
        for series_id, info in RECEIVER_SERIES.items()
    ]


def get_supported_sets(series_id: str) -> list:
    """Get supported command sets for a receiver series."""
    if series_id in RECEIVER_SERIES:
        return RECEIVER_SERIES[series_id]["supported_sets"]
    return ["set1"]  # Fallback to basic commands


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
CMD_TONE_BASS = "TFR"       # Tone Front Bass
CMD_TONE_TREBLE = "TFT"     # Tone Front Treble
CMD_SLEEP = "SLP"           # Sleep Timer
CMD_DISPLAY = "DIF"         # Display Mode
CMD_DIMMER = "DIM"          # Dimmer Level
CMD_HDMI_OUTPUT = "HDO"     # HDMI Output Selector
CMD_HDMI_AUDIO = "HAO"      # HDMI Audio Output
CMD_VIDEO_WIDE = "VWM"      # Video Wide Mode
CMD_VIDEO_RESOLUTION = "RES" # Video Resolution
CMD_PHASE_CONTROL = "PCT"   # Phase Control
CMD_CENTER_LEVEL = "CTL"    # Center Level
CMD_SUBWOOFER_LEVEL = "SWL" # Subwoofer Level
CMD_MUSIC_OPTIMIZER = "MOT" # Music Optimizer
CMD_AV_SYNC = "AVS"         # A/V Sync
CMD_HDMI_CEC = "CEC"        # HDMI CEC

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
    "00": "VIDEO1",
    "01": "CBL/SAT",
    "02": "GAME",
    "03": "AUX",
    "04": "AUX2",
    "05": "PC",
    "06": "VIDEO6",
    "07": "VIDEO7",
    "10": "BD/DVD",
    "11": "STRM BOX",
    "12": "TV",
    "13": "TAPE1",
    "14": "TAPE2",
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
    "30": "MULTI CH",
    "31": "XM",
    "32": "SIRIUS",
    "33": "DAB",
    "40": "UNIVERSAL PORT",
    "41": "LINE",
    "42": "LINE2",
    "55": "HDMI5",
    "56": "HDMI6",
    "57": "HDMI7",
    "80": "SOURCE",
}

SOURCE_TO_CODE = {v: k for k, v in INPUT_SOURCES.items()}


def get_sources_for_series(series_id: str) -> list:
    """
    Get available input sources for a receiver series.
    Returns a list of source names that can be used in SOURCE_LIST attribute.
    """
    # Common sources for all receivers (set1)
    common_sources = [
        "BD/DVD", "CBL/SAT", "GAME", "TV", "STRM BOX",
        "CD", "TUNER", "PHONO", "AUX",
        "NETWORK", "USB FRONT", "MUSIC SERVER", "INTERNET RADIO",
    ]
    
    # Additional sources by series
    series_sources = {
        "TX-NR5xx": common_sources + ["BLUETOOTH", "AIRPLAY", "USB DAC", "PC", "AM", "FM"],
        "TX-NR6xx": common_sources + ["BLUETOOTH", "AIRPLAY", "USB DAC", "PC", "AM", "FM"],
        "TX-NR7xx": common_sources + ["BLUETOOTH", "AIRPLAY", "USB DAC", "PC", "AM", "FM", "MULTI CH"],
        "TX-RZxxx": common_sources + ["BLUETOOTH", "AIRPLAY", "USB DAC", "PC", "AM", "FM", "MULTI CH"],
        "TX-NR8xx-9xx": common_sources + ["BLUETOOTH", "AIRPLAY", "PC", "AM", "FM", "MULTI CH"],
        "GENERIC": common_sources,
    }
    
    return series_sources.get(series_id, common_sources)


# =============================================================================
# Input Source Labels - Human-readable names for Remote Two display
# =============================================================================
INPUT_SOURCE_LABELS = {
    "VIDEO1": "Video 1",
    "CBL/SAT": "Cable / Satellite",
    "GAME": "Game",
    "AUX": "AUX",
    "AUX2": "AUX 2",
    "PC": "PC",
    "BD/DVD": "Blu-ray / DVD",
    "STRM BOX": "Streaming Box",
    "TV": "TV",
    "PHONO": "Phono",
    "TV/CD": "TV / CD",
    "TUNER": "Tuner",
    "CD": "CD",
    "FM": "FM Radio",
    "AM": "AM Radio",
    "MUSIC SERVER": "Music Server",
    "INTERNET RADIO": "Internet Radio",
    "USB FRONT": "USB (Front)",
    "USB REAR": "USB (Rear)",
    "NETWORK": "Network",
    "BLUETOOTH": "Bluetooth",
    "AIRPLAY": "AirPlay",
    "USB DAC": "USB DAC",
    "MULTI CH": "Multi-Channel",
    "LINE": "Line In",
    "LINE2": "Line In 2",
}


def get_source_label(source_name: str) -> str:
    """Get human-readable label for a source name."""
    return INPUT_SOURCE_LABELS.get(source_name, source_name)


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
    "40": "STRAIGHT DECODE",
    "41": "DOLBY EX/DTS ES",
    "42": "THX CINEMA",
    "43": "THX SURROUND EX",
    "44": "THX MUSIC",
    "45": "THX GAMES",
    "80": "PLII/PLIIx MOVIE",
    "81": "PLII/PLIIx MUSIC",
    "82": "NEO:6 CINEMA",
    "83": "NEO:6 MUSIC",
    "84": "PLII/PLIIx THX CINEMA",
    "85": "NEO:6 THX CINEMA",
    "86": "PLII/PLIIx GAME",
    "FF": "AUTO SURROUND",
}

LISTENING_MODE_TO_CODE = {v: k for k, v in LISTENING_MODES.items()}


# =============================================================================
# Listening Mode Labels
# =============================================================================
LISTENING_MODE_LABELS = {
    "STEREO": "Stereo",
    "DIRECT": "Direct",
    "SURROUND": "Surround",
    "FILM": "Film",
    "THX": "THX",
    "ACTION": "Action",
    "MUSICAL": "Musical",
    "MONO MOVIE": "Mono Movie",
    "ORCHESTRA": "Orchestra",
    "UNPLUGGED": "Unplugged",
    "STUDIO-MIX": "Studio Mix",
    "TV LOGIC": "TV Logic",
    "ALL CH STEREO": "All Channel Stereo",
    "THEATER-DIMENSIONAL": "Theater Dimensional",
    "ENHANCED": "Enhanced",
    "MONO": "Mono",
    "PURE AUDIO": "Pure Audio",
    "STRAIGHT DECODE": "Straight Decode",
    "DOLBY EX/DTS ES": "Dolby EX / DTS ES",
    "THX CINEMA": "THX Cinema",
    "THX SURROUND EX": "THX Surround EX",
    "THX MUSIC": "THX Music",
    "THX GAMES": "THX Games",
    "PLII/PLIIx MOVIE": "Dolby PLII Movie",
    "PLII/PLIIx MUSIC": "Dolby PLII Music",
    "NEO:6 CINEMA": "DTS Neo:6 Cinema",
    "NEO:6 MUSIC": "DTS Neo:6 Music",
    "AUTO SURROUND": "Auto Surround",
}


def get_listening_mode_label(mode_name: str) -> str:
    """Get human-readable label for a listening mode."""
    return LISTENING_MODE_LABELS.get(mode_name, mode_name)


# =============================================================================
# Simple Commands with Set Requirements
# Format: "COMMAND_NAME": ("required_set", (CMD_CODE, "value"))
# set1 = Basic commands (all receivers)
# set2+ = Extended features (specific series)
# =============================================================================
SIMPLE_COMMAND_DEFINITIONS = {
    # Power - set1 (all receivers)
    "POWER_ON": ("set1", (CMD_POWER, "01")),
    "POWER_OFF": ("set1", (CMD_POWER, "00")),
    "POWER_TOGGLE": ("set1", (CMD_POWER, "QSTN")),
    
    # Volume - set1 (all receivers)
    "VOLUME_UP": ("set1", (CMD_VOLUME, "UP")),
    "VOLUME_DOWN": ("set1", (CMD_VOLUME, "DOWN")),
    "MUTE_ON": ("set1", (CMD_MUTE, "01")),
    "MUTE_OFF": ("set1", (CMD_MUTE, "00")),
    "MUTE_TOGGLE": ("set1", (CMD_MUTE, "TG")),
    
    # Input Selection - set1 (basic inputs)
    "INPUT_BD_DVD": ("set1", (CMD_INPUT, "10")),
    "INPUT_CBL_SAT": ("set1", (CMD_INPUT, "01")),
    "INPUT_GAME": ("set1", (CMD_INPUT, "02")),
    "INPUT_AUX": ("set1", (CMD_INPUT, "03")),
    "INPUT_TV": ("set1", (CMD_INPUT, "12")),
    "INPUT_STRM_BOX": ("set1", (CMD_INPUT, "11")),
    "INPUT_CD": ("set1", (CMD_INPUT, "23")),
    "INPUT_PHONO": ("set1", (CMD_INPUT, "22")),
    "INPUT_TUNER": ("set1", (CMD_INPUT, "26")),
    "INPUT_FM": ("set1", (CMD_INPUT, "24")),
    "INPUT_AM": ("set1", (CMD_INPUT, "25")),
    "INPUT_PC": ("set1", (CMD_INPUT, "05")),
    
    # Network/USB Inputs - set3 (newer receivers)
    "INPUT_USB": ("set3", (CMD_INPUT, "29")),
    "INPUT_NETWORK": ("set3", (CMD_INPUT, "2B")),
    "INPUT_BLUETOOTH": ("set3", (CMD_INPUT, "2D")),
    "INPUT_AIRPLAY": ("set3", (CMD_INPUT, "2E")),
    "INPUT_MUSIC_SERVER": ("set3", (CMD_INPUT, "27")),
    "INPUT_INTERNET_RADIO": ("set3", (CMD_INPUT, "28")),
    
    # USB DAC / Line inputs - set2 (specific models)
    "INPUT_USB_DAC": ("set2", (CMD_INPUT, "2F")),
    "INPUT_LINE": ("set2", (CMD_INPUT, "41")),
    "INPUT_LINE2": ("set2", (CMD_INPUT, "42")),
    
    # Listening Modes - set1 (basic)
    "LISTENING_MODE_STEREO": ("set1", (CMD_LISTENING_MODE, "00")),
    "LISTENING_MODE_DIRECT": ("set1", (CMD_LISTENING_MODE, "01")),
    "LISTENING_MODE_SURROUND": ("set1", (CMD_LISTENING_MODE, "02")),
    "LISTENING_MODE_FILM": ("set1", (CMD_LISTENING_MODE, "03")),
    "LISTENING_MODE_MUSIC": ("set1", (CMD_LISTENING_MODE, "06")),
    "LISTENING_MODE_GAME": ("set1", (CMD_LISTENING_MODE, "05")),
    "LISTENING_MODE_THX": ("set1", (CMD_LISTENING_MODE, "04")),
    "LISTENING_MODE_ALL_CH_STEREO": ("set1", (CMD_LISTENING_MODE, "0C")),
    "LISTENING_MODE_PURE_AUDIO": ("set1", (CMD_LISTENING_MODE, "11")),
    "LISTENING_MODE_AUTO": ("set1", (CMD_LISTENING_MODE, "FF")),
    "LISTENING_MODE_UP": ("set1", (CMD_LISTENING_MODE, "UP")),
    "LISTENING_MODE_DOWN": ("set1", (CMD_LISTENING_MODE, "DOWN")),
    
    # Dimmer - set1
    "DIMMER_BRIGHT": ("set1", (CMD_DIMMER, "00")),
    "DIMMER_DIM": ("set1", (CMD_DIMMER, "01")),
    "DIMMER_DARK": ("set1", (CMD_DIMMER, "02")),
    "DIMMER_OFF": ("set1", (CMD_DIMMER, "03")),
    "DIMMER_TOGGLE": ("set1", (CMD_DIMMER, "DIM")),
    
    # Display - set1
    "DISPLAY_TOGGLE": ("set1", (CMD_DISPLAY, "TG")),
    
    # Late Night Mode - set1
    "LATE_NIGHT_OFF": ("set1", (CMD_LATE_NIGHT, "00")),
    "LATE_NIGHT_LOW": ("set1", (CMD_LATE_NIGHT, "01")),
    "LATE_NIGHT_HIGH": ("set1", (CMD_LATE_NIGHT, "02")),
    "LATE_NIGHT_AUTO": ("set1", (CMD_LATE_NIGHT, "03")),
    
    # Audyssey - set3 (newer receivers with Audyssey)
    "AUDYSSEY_OFF": ("set3", (CMD_AUDYSSEY, "00")),
    "AUDYSSEY_MOVIE": ("set3", (CMD_AUDYSSEY, "01")),
    "AUDYSSEY_MUSIC": ("set3", (CMD_AUDYSSEY, "02")),
    "DYNAMIC_EQ_ON": ("set3", (CMD_AUDYSSEY_EQ, "01")),
    "DYNAMIC_EQ_OFF": ("set3", (CMD_AUDYSSEY_EQ, "00")),
    "DYNAMIC_VOLUME_OFF": ("set3", (CMD_AUDYSSEY_VOL, "00")),
    "DYNAMIC_VOLUME_LIGHT": ("set3", (CMD_AUDYSSEY_VOL, "01")),
    "DYNAMIC_VOLUME_MEDIUM": ("set3", (CMD_AUDYSSEY_VOL, "02")),
    "DYNAMIC_VOLUME_HEAVY": ("set3", (CMD_AUDYSSEY_VOL, "03")),
    
    # HDMI Output - set3
    "HDMI_OUT_MAIN": ("set3", (CMD_HDMI_OUTPUT, "01")),
    "HDMI_OUT_SUB": ("set3", (CMD_HDMI_OUTPUT, "02")),
    "HDMI_OUT_BOTH": ("set3", (CMD_HDMI_OUTPUT, "03")),
    "HDMI_OUT_OFF": ("set3", (CMD_HDMI_OUTPUT, "00")),
    
    # OSD/Menu Navigation - set1
    "MENU": ("set1", (CMD_OSD_MENU, "MENU")),
    "EXIT": ("set1", (CMD_OSD_MENU, "EXIT")),
    "UP": ("set1", (CMD_OSD_MENU, "UP")),
    "DOWN": ("set1", (CMD_OSD_MENU, "DOWN")),
    "LEFT": ("set1", (CMD_OSD_MENU, "LEFT")),
    "RIGHT": ("set1", (CMD_OSD_MENU, "RIGHT")),
    "ENTER": ("set1", (CMD_OSD_MENU, "ENTER")),
    "RETURN": ("set1", (CMD_OSD_MENU, "RETURN")),
    "HOME": ("set1", (CMD_OSD_MENU, "HOME")),
    "QUICK_SETUP": ("set1", (CMD_OSD_MENU, "QUICK")),
    "AUDIO_INFO": ("set1", (CMD_AUDIO_INFO, "QSTN")),
    "VIDEO_INFO": ("set1", (CMD_VIDEO_INFO, "QSTN")),
    
    # Playback Control - set3 (network capable)
    "PLAY": ("set3", (CMD_NET_USB_PLAY, "PLAY")),
    "PAUSE": ("set3", (CMD_NET_USB_PLAY, "PAUSE")),
    "STOP": ("set3", (CMD_NET_USB_PLAY, "STOP")),
    "PREVIOUS": ("set3", (CMD_NET_USB_PLAY, "TRDN")),
    "NEXT": ("set3", (CMD_NET_USB_PLAY, "TRUP")),
    "FAST_FORWARD": ("set3", (CMD_NET_USB_PLAY, "FF")),
    "REWIND": ("set3", (CMD_NET_USB_PLAY, "REW")),
    "REPEAT": ("set3", (CMD_NET_USB_PLAY, "REPEAT")),
    "SHUFFLE": ("set3", (CMD_NET_USB_PLAY, "RANDOM")),
    
    # Tuner - set1
    "TUNER_PRESET_UP": ("set1", (CMD_TUNER_PRESET, "UP")),
    "TUNER_PRESET_DOWN": ("set1", (CMD_TUNER_PRESET, "DOWN")),
    "TUNER_FREQ_UP": ("set1", (CMD_TUNER_FREQ, "UP")),
    "TUNER_FREQ_DOWN": ("set1", (CMD_TUNER_FREQ, "DOWN")),
    "TUNER_MODE_FM": ("set1", (CMD_TUNER_MODE, "00")),
    "TUNER_MODE_AM": ("set1", (CMD_TUNER_MODE, "01")),
    
    # Zone 2 - set7 (multi-zone capable)
    "ZONE2_POWER_ON": ("set7", (CMD_ZONE2_POWER, "01")),
    "ZONE2_POWER_OFF": ("set7", (CMD_ZONE2_POWER, "00")),
    "ZONE2_VOLUME_UP": ("set7", (CMD_ZONE2_VOLUME, "UP")),
    "ZONE2_VOLUME_DOWN": ("set7", (CMD_ZONE2_VOLUME, "DOWN")),
    "ZONE2_MUTE_TOGGLE": ("set7", (CMD_ZONE2_MUTE, "TG")),
    
    # Speaker A/B - set3/set7
    "SPEAKER_A_ON": ("set3", (CMD_SPEAKER_A, "01")),
    "SPEAKER_A_OFF": ("set3", (CMD_SPEAKER_A, "00")),
    "SPEAKER_B_ON": ("set7", (CMD_SPEAKER_B, "01")),
    "SPEAKER_B_OFF": ("set7", (CMD_SPEAKER_B, "00")),
    
    # Sleep Timer - set1
    "SLEEP_OFF": ("set1", (CMD_SLEEP, "OFF")),
    "SLEEP_30": ("set1", (CMD_SLEEP, "1E")),
    "SLEEP_60": ("set1", (CMD_SLEEP, "3C")),
    "SLEEP_90": ("set1", (CMD_SLEEP, "5A")),
    
    # Memory - set1
    "MEMORY_SETUP": ("set1", (CMD_MEMORY, "STR")),
}


# =============================================================================
# Simple Command Labels - Human-readable names for Remote Two buttons
# =============================================================================
SIMPLE_COMMAND_LABELS = {
    "POWER_ON": "Power On",
    "POWER_OFF": "Power Off",
    "POWER_TOGGLE": "Power Toggle",
    "VOLUME_UP": "Volume Up",
    "VOLUME_DOWN": "Volume Down",
    "MUTE_ON": "Mute On",
    "MUTE_OFF": "Mute Off",
    "MUTE_TOGGLE": "Mute Toggle",
    "INPUT_BD_DVD": "Blu-ray / DVD",
    "INPUT_CBL_SAT": "Cable / Satellite",
    "INPUT_GAME": "Game",
    "INPUT_AUX": "AUX",
    "INPUT_TV": "TV",
    "INPUT_STRM_BOX": "Streaming Box",
    "INPUT_CD": "CD",
    "INPUT_PHONO": "Phono",
    "INPUT_TUNER": "Tuner",
    "INPUT_FM": "FM Radio",
    "INPUT_AM": "AM Radio",
    "INPUT_USB": "USB",
    "INPUT_NETWORK": "Network",
    "INPUT_BLUETOOTH": "Bluetooth",
    "INPUT_AIRPLAY": "AirPlay",
    "INPUT_MUSIC_SERVER": "Music Server",
    "INPUT_INTERNET_RADIO": "Internet Radio",
    "INPUT_PC": "PC",
    "INPUT_USB_DAC": "USB DAC",
    "INPUT_LINE": "Line In",
    "INPUT_LINE2": "Line In 2",
    "LISTENING_MODE_STEREO": "Stereo",
    "LISTENING_MODE_DIRECT": "Direct",
    "LISTENING_MODE_SURROUND": "Surround",
    "LISTENING_MODE_FILM": "Film",
    "LISTENING_MODE_MUSIC": "Music",
    "LISTENING_MODE_GAME": "Game",
    "LISTENING_MODE_THX": "THX",
    "LISTENING_MODE_ALL_CH_STEREO": "All Ch Stereo",
    "LISTENING_MODE_PURE_AUDIO": "Pure Audio",
    "LISTENING_MODE_AUTO": "Auto Surround",
    "LISTENING_MODE_UP": "Mode Up",
    "LISTENING_MODE_DOWN": "Mode Down",
    "DIMMER_BRIGHT": "Display Bright",
    "DIMMER_DIM": "Display Dim",
    "DIMMER_DARK": "Display Dark",
    "DIMMER_OFF": "Display Off",
    "DIMMER_TOGGLE": "Dimmer Toggle",
    "DISPLAY_TOGGLE": "Display Toggle",
    "LATE_NIGHT_OFF": "Late Night Off",
    "LATE_NIGHT_LOW": "Late Night Low",
    "LATE_NIGHT_HIGH": "Late Night High",
    "LATE_NIGHT_AUTO": "Late Night Auto",
    "AUDYSSEY_OFF": "Audyssey Off",
    "AUDYSSEY_MOVIE": "Audyssey Movie",
    "AUDYSSEY_MUSIC": "Audyssey Music",
    "DYNAMIC_EQ_ON": "Dynamic EQ On",
    "DYNAMIC_EQ_OFF": "Dynamic EQ Off",
    "DYNAMIC_VOLUME_OFF": "Dynamic Vol Off",
    "DYNAMIC_VOLUME_LIGHT": "Dynamic Vol Light",
    "DYNAMIC_VOLUME_MEDIUM": "Dynamic Vol Medium",
    "DYNAMIC_VOLUME_HEAVY": "Dynamic Vol Heavy",
    "HDMI_OUT_MAIN": "HDMI Out Main",
    "HDMI_OUT_SUB": "HDMI Out Sub",
    "HDMI_OUT_BOTH": "HDMI Out Both",
    "HDMI_OUT_OFF": "HDMI Out Off",
    "MENU": "Menu",
    "EXIT": "Exit",
    "UP": "Up",
    "DOWN": "Down",
    "LEFT": "Left",
    "RIGHT": "Right",
    "ENTER": "Enter",
    "RETURN": "Return",
    "HOME": "Home",
    "QUICK_SETUP": "Quick Setup",
    "AUDIO_INFO": "Audio Info",
    "VIDEO_INFO": "Video Info",
    "PLAY": "Play",
    "PAUSE": "Pause",
    "STOP": "Stop",
    "PREVIOUS": "Previous",
    "NEXT": "Next",
    "FAST_FORWARD": "Fast Forward",
    "REWIND": "Rewind",
    "REPEAT": "Repeat",
    "SHUFFLE": "Shuffle",
    "TUNER_PRESET_UP": "Preset Up",
    "TUNER_PRESET_DOWN": "Preset Down",
    "TUNER_FREQ_UP": "Frequency Up",
    "TUNER_FREQ_DOWN": "Frequency Down",
    "TUNER_MODE_FM": "FM Mode",
    "TUNER_MODE_AM": "AM Mode",
    "ZONE2_POWER_ON": "Zone 2 On",
    "ZONE2_POWER_OFF": "Zone 2 Off",
    "ZONE2_VOLUME_UP": "Zone 2 Vol Up",
    "ZONE2_VOLUME_DOWN": "Zone 2 Vol Down",
    "ZONE2_MUTE_TOGGLE": "Zone 2 Mute",
    "SPEAKER_A_ON": "Speaker A On",
    "SPEAKER_A_OFF": "Speaker A Off",
    "SPEAKER_B_ON": "Speaker B On",
    "SPEAKER_B_OFF": "Speaker B Off",
    "SLEEP_OFF": "Sleep Off",
    "SLEEP_30": "Sleep 30 min",
    "SLEEP_60": "Sleep 60 min",
    "SLEEP_90": "Sleep 90 min",
    "MEMORY_SETUP": "Memory Setup",
}


def get_command_label(command: str) -> str:
    """Get human-readable label for a simple command."""
    return SIMPLE_COMMAND_LABELS.get(command, command)


# =============================================================================
# Functions to get filtered commands based on receiver series
# =============================================================================

def get_commands_for_series(series_id: str) -> list:
    """
    Get list of supported command names for a receiver series.
    
    :param series_id: Receiver series ID (e.g., "TX-NR6xx")
    :return: List of command names supported by this series
    """
    supported_sets = get_supported_sets(series_id)
    commands = []
    
    for cmd_name, (required_set, _) in SIMPLE_COMMAND_DEFINITIONS.items():
        if required_set in supported_sets:
            commands.append(cmd_name)
    
    return commands


def get_command_map_for_series(series_id: str) -> dict:
    """
    Get command map (name -> (cmd, value)) for a receiver series.
    Only includes commands supported by this series.
    
    :param series_id: Receiver series ID
    :return: Dict mapping command name to (CMD_CODE, value) tuple
    """
    supported_sets = get_supported_sets(series_id)
    cmd_map = {}
    
    for cmd_name, (required_set, cmd_tuple) in SIMPLE_COMMAND_DEFINITIONS.items():
        if required_set in supported_sets:
            cmd_map[cmd_name] = cmd_tuple
    
    return cmd_map


def is_command_supported(command: str, series_id: str) -> bool:
    """
    Check if a command is supported by a receiver series.
    
    :param command: Command name
    :param series_id: Receiver series ID
    :return: True if supported
    """
    if command not in SIMPLE_COMMAND_DEFINITIONS:
        return False
    
    required_set = SIMPLE_COMMAND_DEFINITIONS[command][0]
    supported_sets = get_supported_sets(series_id)
    
    return required_set in supported_sets


# =============================================================================
# Legacy compatibility - SIMPLE_COMMANDS list and SIMPLE_COMMAND_MAP
# These are populated for the default (all commands) case
# =============================================================================
SIMPLE_COMMANDS = list(SIMPLE_COMMAND_DEFINITIONS.keys())

SIMPLE_COMMAND_MAP = {
    cmd_name: cmd_tuple 
    for cmd_name, (_, cmd_tuple) in SIMPLE_COMMAND_DEFINITIONS.items()
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