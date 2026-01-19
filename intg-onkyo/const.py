"""Constants for Onkyo integration."""

DRIVER_ID = "onkyo"
DRIVER_VERSION = "0.1.0"

# eISCP Protocol
EISCP_PORT = 60128
DISCOVERY_PORT = 60128
DISCOVERY_TIMEOUT = 5

# Commands
CMD_POWER = "PWR"
CMD_VOLUME = "MVL"
CMD_MUTE = "AMT"
CMD_INPUT = "SLI"

# Power states
POWER_ON = "01"
POWER_OFF = "00"
POWER_QUERY = "QSTN"

# Mute states
MUTE_ON = "01"
MUTE_OFF = "00"

# Volume (0-80 in hex, mapped to 0-100%)
VOLUME_MIN = 0
VOLUME_MAX = 80

# Onkyo TX-NR696 Input Sources
INPUT_SOURCES = {
    "00": "VIDEO1",
    "01": "VIDEO2",
    "02": "VIDEO3",
    "03": "VIDEO4",
    "04": "VIDEO5",
    "05": "VIDEO6",
    "06": "VIDEO7",
    "10": "DVD",
    "20": "TAPE1",
    "21": "TAPE2",
    "22": "PHONO",
    "23": "CD",
    "24": "FM",
    "25": "AM",
    "26": "TUNER",
    "27": "MUSIC SERVER",
    "28": "INTERNET RADIO",
    "29": "USB",
    "2A": "USB_BACK",
    "2B": "NETWORK",
    "2C": "USB_TOGGLE",
    "40": "UNIVERSAL PORT",
    "30": "MULTI CH",
    "31": "XM",
    "32": "SIRIUS",
    "12": "TV/CD",
    "80": "SOURCE",
    "81": "BD/DVD",
    "82": "GAME",
    "83": "AUX",
    "84": "GAME2",
    "85": "CBL/SAT",
    "86": "HOME NETWORK",
    "2D": "BLUETOOTH",
    "2E": "AIRPLAY",
    "41": "HDMI5",
    "42": "HDMI6",
    "43": "HDMI7",
}

SOURCE_TO_CODE = {v: k for k, v in INPUT_SOURCES.items()}
