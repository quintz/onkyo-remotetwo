"""
Input and listening mode names.

- Correct eISCP code tables (SLI = input selector, LMD = listening mode).
  Verified against the official Onkyo eISCP spec / onkyo-eiscp command list.
- Listening mode codes were re-used by Onkyo: models from 2016 on (e.g.
  TX-NR656/676/686/696, RZ series) show "Dolby Surround" for 80, "DTS Neural:X"
  for 82 and Game-RPG/Action/Rock/Sports for 03/05/06/0E. Older models show
  PLII/Neo:6/Film/Action/Musical. Both name sets are kept here.
- Per device the user can define which inputs/modes appear and how they are
  named ("Code = Name" lines in the setup). Input names can also be read from
  the receiver itself (NRIQSTN -> <selectorlist>).

:copyright: (c) 2026 by Quirin.
:license: Mozilla Public License Version 2.0, see LICENSE for more details.
"""

from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

_LOG = logging.getLogger(__name__)

# =============================================================================
# Input selector (SLI)
# =============================================================================

# Canonical names as shown on the receiver display (NR686 style).
INPUT_NAMES: dict[str, str] = {
    "00": "VIDEO1",
    "01": "CBL/SAT",
    "02": "GAME",
    "03": "AUX",
    "04": "AUX2",
    "05": "PC",
    "06": "VIDEO7",
    "07": "EXTRA1",
    "08": "EXTRA2",
    "09": "EXTRA3",
    "10": "BD/DVD",
    "11": "STRM BOX",
    "12": "TV",
    "20": "TAPE",
    "21": "TAPE2",
    "22": "PHONO",
    "23": "CD",
    "24": "FM",
    "25": "AM",
    "26": "TUNER",
    "27": "MUSIC SERVER",
    "28": "INTERNET RADIO",
    "29": "USB",
    "2A": "USB REAR",
    "2B": "NET",
    "2C": "USB TOGGLE",
    "2D": "AIRPLAY",
    "2E": "BLUETOOTH",
    "2F": "USB DAC",
    "30": "MULTI CH",
    "31": "XM",
    "32": "SIRIUS",
    "33": "DAB",
    "40": "UNIVERSAL PORT",
    "41": "LINE",
    "42": "LINE2",
    "44": "OPTICAL",
    "45": "COAXIAL",
    "55": "HDMI5",
    "56": "HDMI6",
    "57": "HDMI7",
    "80": "SOURCE",
}

# Names used by v0.4.x (some pointed to the wrong code) and other common
# spellings. Kept so existing activities using e.g. "NETWORK" still work.
INPUT_ALIASES: dict[str, str] = {
    "NETWORK": "2B",
    "USB FRONT": "29",
    "USB (FRONT)": "29",
    "USB (REAR)": "2A",
    "TV/CD": "23",
    "TV/TAPE": "20",
    "TAPE1": "20",
    "VIDEO2": "01",
    "VIDEO3": "02",
    "VIDEO4": "03",
    "VIDEO5": "04",
    "VIDEO6": "05",
    "AUX1": "03",
    "GAME2": "04",
    "DVD": "10",
    "BD": "10",
    "STREAMING BOX": "11",
    "STRM-BOX": "11",
    "DLNA": "27",
    "BT": "2E",
}

# Inputs of current Onkyo receivers like the TX-NR686 (used when the receiver
# doesn't report its own list).
DEFAULT_INPUTS = ["10", "01", "11", "05", "02", "03", "12", "23", "22", "24", "25", "2B", "29", "2E"]


# =============================================================================
# Listening modes (LMD)
# =============================================================================

# Models from 2016 on (TX-NR656/676/686/696, TX-RZ...).
MODE_NAMES_MODERN: dict[str, str] = {
    "00": "Stereo",
    "01": "Direct",
    "02": "Surround",
    "03": "Game-RPG",
    "04": "THX",
    "05": "Game-Action",
    "06": "Game-Rock",
    "07": "Mono Movie",
    "08": "Classical",
    "09": "Unplugged",
    "0A": "Entertainment Show",
    "0B": "Drama",
    "0C": "AllCh Stereo",
    "0D": "Theater-Dimensional",
    "0E": "Game-Sports",
    "0F": "Mono",
    "11": "Pure Direct",
    "12": "Multiplex",
    "13": "Full Mono",
    "14": "Dolby Virtual",
    "15": "DTS Surround Sensation",
    "16": "Audyssey DSX",
    "17": "DTS Virtual:X",
    "1F": "Whole House",
    "40": "Straight Decode",
    "41": "Dolby EX/DTS-ES",
    "42": "THX Cinema",
    "43": "THX Surround EX",
    "44": "THX Music",
    "45": "THX Games",
    "50": "THX Cinema 2",
    "51": "THX Music 2",
    "52": "THX Games 2",
    "80": "Dolby Atmos/Surround",
    "82": "DTS:X/Neural:X",
    "84": "Dolby Surround THX Cinema",
    "85": "Neural:X THX Cinema",
    "89": "Dolby Surround THX Games",
    "8A": "Neural:X THX Games",
    "8B": "Dolby Surround THX Music",
    "8C": "Neural:X THX Music",
    "FF": "Auto Surround",
}

# Models before 2016 (Dolby PLII, DTS Neo:6, Theater/Film/Musical modes).
MODE_NAMES_LEGACY: dict[str, str] = {
    "00": "Stereo",
    "01": "Direct",
    "02": "Surround",
    "03": "Film",
    "04": "THX",
    "05": "Action",
    "06": "Musical",
    "07": "Mono Movie",
    "08": "Orchestra",
    "09": "Unplugged",
    "0A": "Studio-Mix",
    "0B": "TV Logic",
    "0C": "All Ch Stereo",
    "0D": "Theater-Dimensional",
    "0E": "Enhanced",
    "0F": "Mono",
    "11": "Pure Audio",
    "12": "Multiplex",
    "13": "Full Mono",
    "14": "Dolby Virtual",
    "15": "DTS Surround Sensation",
    "16": "Audyssey DSX",
    "1F": "Whole House",
    "40": "Straight Decode",
    "41": "Dolby EX/DTS-ES",
    "42": "THX Cinema",
    "43": "THX Surround EX",
    "44": "THX Music",
    "45": "THX Games",
    "50": "THX U2/S2 Cinema",
    "51": "THX U2/S2 Music",
    "52": "THX U2/S2 Games",
    "80": "PLII Movie",
    "81": "PLII Music",
    "82": "Neo:6 Cinema",
    "83": "Neo:6 Music",
    "84": "PLII THX Cinema",
    "85": "Neo:6 THX Cinema",
    "86": "PLII Game",
    "87": "Neural Surround",
    "88": "Neural THX",
    "89": "PLII THX Games",
    "8A": "Neo:6 THX Games",
    "8B": "PLII THX Music",
    "8C": "Neo:6 THX Music",
    "90": "PLIIz Height",
    "93": "Neural Digital Music",
    "9A": "Neo:X Game",
    "A0": "PLII Movie + DSX",
    "A1": "PLII Music + DSX",
    "A2": "PLII Game + DSX",
    "A3": "Neo:6 Cinema + DSX",
    "A4": "Neo:6 Music + DSX",
    "A7": "Dolby EX + DSX",
    "FF": "Auto Surround",
}

# Selectable modes of a TX-NR686 class receiver (2016+).
DEFAULT_MODES_MODERN = ["00", "01", "11", "0F", "40", "80", "82", "17", "0C", "13", "0D", "03", "05", "06", "0E"]
# Typical modes of older receivers.
DEFAULT_MODES_LEGACY = ["00", "01", "11", "0F", "40", "80", "81", "86", "82", "83", "0C", "13", "0D", "03", "05", "06", "08", "0A"]

# v0.4.x names (upper case) -> code, so stored activities keep working.
MODE_ALIASES: dict[str, str] = {
    "STEREO": "00",
    "DIRECT": "01",
    "SURROUND": "02",
    "FILM": "03",
    "ACTION": "05",
    "MUSICAL": "06",
    "MONO MOVIE": "07",
    "ORCHESTRA": "08",
    "UNPLUGGED": "09",
    "STUDIO-MIX": "0A",
    "TV LOGIC": "0B",
    "ALL CH STEREO": "0C",
    "EXT.STEREO": "0C",
    "THEATER-DIMENSIONAL": "0D",
    "T-D": "0D",
    "ENHANCED": "0E",
    "MONO": "0F",
    "PURE AUDIO": "11",
    "PURE DIRECT": "11",
    "MULTIPLEX": "12",
    "FULL MONO": "13",
    "STRAIGHT DECODE": "40",
    "MULTICHANNEL": "40",
    "DOLBY EX/DTS ES": "41",
    "THX CINEMA": "42",
    "THX SURROUND EX": "43",
    "THX MUSIC": "44",
    "THX GAMES": "45",
    "PLII/PLIIX MOVIE": "80",
    "DOLBY SURROUND": "80",
    "DOLBY ATMOS": "80",
    "PLII/PLIIX MUSIC": "81",
    "NEO:6 CINEMA": "82",
    "NEURAL:X": "82",
    "DTS NEURAL:X": "82",
    "DTS:X": "82",
    "NEO:6 MUSIC": "83",
    "PLII/PLIIX THX CINEMA": "84",
    "NEO:6 THX CINEMA": "85",
    "PLII/PLIIX GAME": "86",
    "AUTO SURROUND": "FF",
}

_CODE_RE = re.compile(r"^[0-9A-Fa-f]{2}$")


# =============================================================================
# Name table
# =============================================================================


class NameTable:
    """Ordered code <-> display name mapping for one device."""

    def __init__(self, entries: list[tuple[str, str]], fallback: dict[str, str], aliases: dict[str, str], unknown_prefix: str):
        """
        :param entries: visible (code, display name) pairs in UI order
        :param fallback: names for codes not in ``entries`` (receiver may report them)
        :param aliases: extra upper-case names that resolve to a code
        """
        self.entries = [(c.upper(), n) for c, n in entries]
        self._fallback = fallback
        self._aliases = aliases
        self._prefix = unknown_prefix
        self._by_code = dict(self.entries)

    @property
    def names(self) -> list[str]:
        """Display names in UI order."""
        return [n for _, n in self.entries]

    @property
    def codes(self) -> list[str]:
        """Codes in UI order."""
        return [c for c, _ in self.entries]

    def name_for(self, code: str) -> str:
        """Display name for a code (also for codes that are hidden)."""
        code = (code or "").upper()
        if code in self._by_code:
            return self._by_code[code]
        if code in self._fallback:
            return self._fallback[code]
        return f"{self._prefix} {code}"

    def code_for(self, name: str) -> str | None:
        """
        Resolve a display name, canonical/old name or raw code to a code.

        Accepts what activities from older versions stored ("BD/DVD",
        "NETWORK", "PLII/PLIIx MOVIE") as well as "SLI 10"-like unknowns.
        """
        if not name:
            return None
        text = name.strip()
        for code, display in self.entries:
            if display == text:
                return code
        upper = text.upper()
        for code, display in self.entries:
            if display.upper() == upper:
                return code
        for code, display in self._fallback.items():
            if display.upper() == upper:
                return code
        if upper in self._aliases:
            return self._aliases[upper]
        if upper.startswith(self._prefix.upper() + " "):
            upper = upper[len(self._prefix) + 1:]
        if _CODE_RE.match(upper):
            return upper
        return None


def make_inputs(entries: list[tuple[str, str]]) -> NameTable:
    """Input name table."""
    return NameTable(entries, INPUT_NAMES, INPUT_ALIASES, "INPUT")


def make_modes(entries: list[tuple[str, str]], modern: bool) -> NameTable:
    """Listening mode name table."""
    fallback = MODE_NAMES_MODERN if modern else MODE_NAMES_LEGACY
    return NameTable(entries, fallback, MODE_ALIASES, "MODE")


def default_inputs() -> list[tuple[str, str]]:
    """Default inputs (NR686 style) with canonical names."""
    return [(c, INPUT_NAMES[c]) for c in DEFAULT_INPUTS]


def default_modes(modern: bool) -> list[tuple[str, str]]:
    """Default listening modes for the receiver generation."""
    names = MODE_NAMES_MODERN if modern else MODE_NAMES_LEGACY
    codes = DEFAULT_MODES_MODERN if modern else DEFAULT_MODES_LEGACY
    return [(c, names[c]) for c in codes]


# =============================================================================
# "Code = Name" text format used in the setup
# =============================================================================


def format_lines(entries: list[tuple[str, str]]) -> str:
    """Entries -> text for a textarea, one "Code = Name" per line."""
    return "\n".join(f"{code} = {name}" for code, name in entries)


def parse_lines(text: str, table: NameTable) -> tuple[list[tuple[str, str]], list[str]]:
    """
    Parse "Code = Name" lines.

    - ``10 = Apple TV``   code with own name
    - ``BD/DVD = Apple TV`` canonical/old name instead of the code
    - ``10``              code with default name
    - empty lines and lines starting with ``#`` are ignored
    - a code listed twice: the first line wins
    - duplicate display names get " 2", " 3" appended

    :return: (entries, errors)
    """
    entries: list[tuple[str, str]] = []
    errors: list[str] = []
    seen_codes: set[str] = set()
    seen_names: set[str] = set()
    for raw in (text or "").replace("\r", "\n").split("\n"):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        left, sep, right = line.partition("=")
        left, right = left.strip(), right.strip()
        code = left.upper() if _CODE_RE.match(left) else table.code_for(left)
        if not code:
            errors.append(line)
            continue
        if code in seen_codes:
            continue
        name = right if sep and right else table.name_for(code)
        base, n = name, 2
        while name.upper() in seen_names:
            name = f"{base} {n}"
            n += 1
        seen_codes.add(code)
        seen_names.add(name.upper())
        entries.append((code, name))
    return entries, errors


# =============================================================================
# Receiver information (NRIQSTN)
# =============================================================================


@dataclass
class ReceiverInfo:
    """Parsed NRI response."""

    model: str = ""
    year: int | None = None
    inputs: list[tuple[str, str]] = field(default_factory=list)

    @property
    def modern(self) -> bool:
        """True for 2016+ models (new listening mode names)."""
        return self.year is None or self.year >= 2016


def parse_nri(xml_text: str) -> ReceiverInfo | None:
    """
    Parse the XML of an NRI message.

    Relevant part (2016+ models)::

        <device id="TX-NR686"><model>TX-NR686</model><year>2017</year>
          <selectorlist count="..">
            <selector id="10" value="1" name="BD/DVD" zone="03" iconid="10"/>
            ...

    ``value="0"`` marks inputs hidden in the receiver's setup, ``zone`` is a
    bit mask (bit 0 = main zone). Names are the ones edited on the receiver.
    """
    if not xml_text:
        return None
    start = xml_text.find("<")
    if start < 0:
        return None
    try:
        root = ET.fromstring(xml_text[start:].strip().rstrip("\x00\x1a"))
    except ET.ParseError as e:
        _LOG.warning("NRI XML could not be parsed: %s", e)
        return None

    device = root.find(".//device")
    if device is None:
        device = root
    info = ReceiverInfo()
    info.model = (device.findtext("model") or device.get("id") or "").strip()
    year = (device.findtext("year") or "").strip()
    info.year = int(year) if year.isdigit() else None

    for sel in device.iter("selector"):
        code = (sel.get("id") or "").strip().upper()
        if not _CODE_RE.match(code) or code == "80":
            continue
        if sel.get("value", "1").strip() == "0":
            continue
        zone = (sel.get("zone") or "").strip()
        if zone:
            try:
                if not int(zone, 16) & 0x01:
                    continue
            except ValueError:
                pass
        name = (sel.get("name") or "").strip() or INPUT_NAMES.get(code, f"INPUT {code}")
        info.inputs.append((code, name))
    return info
