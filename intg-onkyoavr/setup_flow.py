"""
Setup flow for the Onkyo integration.

Step 1  receiver series, IP address, name (driver.json setup_data_schema)
        -> the receiver is asked for its info (NRIQSTN): model, year and the
           input names as edited on the receiver
Step 2  editable lists "Code = Name" for inputs and listening modes,
        prefilled from the saved config, the receiver or the defaults

Running the setup again (reconfigure) offers: edit names of a receiver,
add another receiver, remove a receiver. Entering the IP of an existing
receiver also updates it instead of failing.

:copyright: (c) 2025-2026 by Quirin.
:license: Mozilla Public License Version 2.0, see LICENSE for more details.
"""

import logging
from typing import Any, Awaitable, Callable

import avr
import config
import names
import ucapi
from config import AvrDevice
from const import RECEIVER_SERIES

_LOG = logging.getLogger(__name__)

# Provides receiver info for an address. The driver replaces this so a running
# connection is reused instead of opening a second one.
receiver_info_provider: Callable[[str], Awaitable[names.ReceiverInfo | None]] = avr.fetch_receiver_info

# Step 1 data kept until the names form is submitted.
_pending: dict[str, Any] = {}

_HELP = {
    "en": (
        "One line per entry: `Code = Name`. **Delete a line** to hide it in the dropdown, **change the name** "
        "to rename it. Instead of the code the standard name works too, e.g. `BD/DVD = Apple TV`. "
        "Leave a field **empty** for automatic (inputs from the receiver, standard listening modes)."
    ),
    "de": (
        "Eine Zeile pro Eintrag: `Code = Name`. **Zeile löschen** = im Dropdown ausblenden, **Name ändern** = "
        "eigener Name. Statt des Codes geht auch der Standardname, z. B. `BD/DVD = Apple TV`. "
        "Feld **leer** lassen = automatisch (Eingänge vom Receiver, Standard-Klangmodi)."
    ),
}


def _text(en: str, de: str | None = None) -> dict[str, str]:
    return {"en": en, "de": de if de is not None else en}


def _label(field_id: str, title: dict[str, str], value: dict[str, str]) -> dict[str, Any]:
    return {"id": field_id, "label": title, "field": {"label": {"value": value}}}


def normalize_address(raw: str) -> str:
    """Accept pasted values like 'http://192.168.1.5/' -> '192.168.1.5'."""
    text = (raw or "").strip()
    if "://" in text:
        text = text.split("://", 1)[1]
    text = text.split("/", 1)[0]
    if text.count(":") == 1:
        text = text.split(":", 1)[0]
    return text.strip()


# =============================================================================
# Forms
# =============================================================================


def _device_form(error: str | None = None, series: str = "TX-NR6xx", address: str = "", name: str = "Onkyo AVR"):
    """Receiver form (same fields as driver.json), used for 'add' and errors."""
    settings: list[dict[str, Any]] = []
    if error:
        settings.append(_label("error", _text("Error", "Fehler"), _text(error)))
    series_items = [{"id": sid, "label": _text(info["label"])} for sid, info in RECEIVER_SERIES.items()]
    settings += [
        {"id": "series", "label": _text("Receiver Series", "Receiver Serie"), "field": {"dropdown": {"value": series, "items": series_items}}},
        {"id": "address", "label": _text("IP Address", "IP-Adresse"), "field": {"text": {"value": address}}},
        {"id": "name", "label": _text("Name"), "field": {"text": {"value": name}}},
    ]
    return ucapi.RequestUserInput(_text("Add Onkyo Receiver", "Onkyo Receiver hinzufügen"), settings)


def _action_form():
    """Reconfigure: what to do."""
    items = []
    for dev in config.devices.all():
        items.append({"id": f"edit:{dev.id}", "label": _text(f"Edit names: {dev.name} ({dev.address})", f"Namen bearbeiten: {dev.name} ({dev.address})")})
    items.append({"id": "add", "label": _text("Add another receiver", "Weiteren Receiver hinzufügen")})
    for dev in config.devices.all():
        items.append({"id": f"remove:{dev.id}", "label": _text(f"Remove: {dev.name} ({dev.address})", f"Entfernen: {dev.name} ({dev.address})")})
    return ucapi.RequestUserInput(
        _text("Configure Onkyo integration", "Onkyo-Integration konfigurieren"),
        [{"id": "action", "label": _text("Action", "Aktion"), "field": {"dropdown": {"value": items[0]["id"], "items": items}}}],
    )


def _other_codes(used: list[tuple[str, str]], table: dict[str, str]) -> str:
    used_codes = {c for c, _ in used}
    return ", ".join(f"`{c}` {n}" for c, n in table.items() if c not in used_codes)


def _names_form(error: str | None = None):
    """Step 2: editable input / listening mode lists."""
    p = _pending
    modern = p["modern"]
    mode_table = names.MODE_NAMES_MODERN if modern else names.MODE_NAMES_LEGACY
    settings: list[dict[str, Any]] = []
    if error:
        settings.append(_label("error", _text("Error", "Fehler"), _text(error)))
    settings.append(_label("status", _text("Receiver"), p["status"]))
    settings.append(_label("help", _text("How it works", "So geht's"), _HELP))
    settings.append({"id": "inputs", "label": _text("Inputs", "Eingänge"), "field": {"textarea": {"value": p["inputs_text"]}}})
    settings.append(
        _label("inputs_more", _text("More input codes", "Weitere Eingangs-Codes"), _text(_other_codes(p["inputs_parsed"], names.INPUT_NAMES)))
    )
    settings.append({"id": "modes", "label": _text("Listening modes", "Klangmodi"), "field": {"textarea": {"value": p["modes_text"]}}})
    settings.append(
        _label("modes_more", _text("More listening mode codes", "Weitere Klangmodus-Codes"), _text(_other_codes(p["modes_parsed"], mode_table)))
    )
    settings.append(
        {
            "id": "naming",
            "label": _text("Listening mode names", "Klangmodus-Namen"),
            "field": {
                "dropdown": {
                    "value": "modern" if modern else "legacy",
                    "items": [
                        {"id": "modern", "label": _text("Models from 2016 (Dolby Surround, Neural:X, Game-…)", "Modelle ab 2016 (Dolby Surround, Neural:X, Game-…)")},
                        {"id": "legacy", "label": _text("Models before 2016 (PLII, Neo:6, Film, Musical…)", "Modelle vor 2016 (PLII, Neo:6, Film, Musical…)")},
                    ],
                }
            },
        }
    )
    return ucapi.RequestUserInput(_text(f"Names: {p['name']}", f"Namen: {p['name']}"), settings)


# =============================================================================
# Steps
# =============================================================================


async def _start_device(series: str, address: str, name: str, existing: AvrDevice | None = None):
    """After step 1: read receiver info and show the names form."""
    address = normalize_address(address)
    if not address:
        return _device_form("Bitte die IP-Adresse eingeben. / Please enter the IP address.", series, address, name)
    device_id = address.replace(".", "_")
    if existing is None and config.devices is not None:
        existing = config.devices.get(device_id)

    _LOG.info("Reading receiver info from %s", address)
    try:
        info = await receiver_info_provider(address)
    except Exception as e:  # noqa: BLE001
        _LOG.warning("Receiver info failed: %s", e)
        info = None

    if existing is not None and existing.modern is not None:
        modern = existing.modern
    elif info is not None:
        modern = info.modern
    else:
        modern = True

    saved_inputs = existing is not None and bool(existing.inputs)
    if saved_inputs:
        inputs = list(existing.inputs)
    elif info is not None and info.inputs:
        inputs = list(info.inputs)
    else:
        inputs = names.default_inputs()
    modes = list(existing.modes) if existing is not None and existing.modes else names.default_modes(modern)

    if info is not None:
        model = f"**{info.model or 'Onkyo'}**" + (f" ({info.year})" if info.year else "")
        if saved_inputs:
            status = _text(f"Detected {model}. Showing your saved lists.", f"Erkannt: {model}. Deine gespeicherten Listen werden angezeigt.")
        elif info.inputs:
            status = _text(f"Detected {model}. Inputs and names were read from the receiver.", f"Erkannt: {model}. Eingänge und Namen wurden vom Receiver übernommen.")
        else:
            status = _text(f"Detected {model}. Standard input list is used.", f"Erkannt: {model}. Es wird die Standard-Eingangsliste verwendet.")
    elif saved_inputs:
        status = _text("Receiver not reachable. Showing your saved lists.", "Receiver nicht erreichbar. Deine gespeicherten Listen werden angezeigt.")
    else:
        status = _text(
            "The receiver didn't report its inputs (not reachable or model too old). Standard list is used.",
            "Der Receiver hat keine Eingangsliste geliefert (nicht erreichbar oder Modell zu alt). Es wird die Standardliste verwendet.",
        )

    _pending.clear()
    _pending.update(
        {
            "id": device_id,
            "series": series or "TX-NR6xx",
            "address": address,
            "name": name or (existing.name if existing else "Onkyo AVR"),
            "model": info.model if info else (existing.model if existing else ""),
            "modern": modern,
            "status": status,
            "inputs_parsed": inputs,
            "modes_parsed": modes,
            "inputs_text": names.format_lines(inputs),
            "modes_text": names.format_lines(modes),
        }
    )
    return _names_form()


def _save_names(values: dict[str, Any]):
    """After step 2: parse lists and save the device."""
    if not _pending:
        _LOG.error("Names submitted without pending device")
        return ucapi.SetupError()
    modern = values.get("naming", "modern" if _pending["modern"] else "legacy") != "legacy"
    inputs_text = str(values.get("inputs", "") or "")
    modes_text = str(values.get("modes", "") or "")

    inputs, bad_inputs = names.parse_lines(inputs_text, names.make_inputs([]))
    modes, bad_modes = names.parse_lines(modes_text, names.make_modes([], modern))
    if bad_inputs or bad_modes:
        _pending.update({"inputs_text": inputs_text, "modes_text": modes_text, "modern": modern})
        bad = "; ".join(bad_inputs + bad_modes)
        return _names_form(f"Unbekannter Code oder Name in: {bad} / Unknown code or name in: {bad}")

    device = AvrDevice(
        id=_pending["id"],
        name=_pending["name"],
        address=_pending["address"],
        series=_pending["series"],
        always_on=True,
        inputs=inputs,
        modes=modes,
        model=_pending["model"],
        modern=modern,
    )
    _pending.clear()
    if config.devices is None:
        _LOG.error("config.devices not initialized")
        return ucapi.SetupError()
    config.devices.add_or_update(device)
    _LOG.info("Saved %s: %d inputs, %d listening modes", device.id, len(inputs), len(modes))
    return ucapi.SetupComplete()


async def _handle_action(action: str):
    if action == "add":
        return _device_form()
    kind, _, device_id = action.partition(":")
    device = config.devices.get(device_id) if config.devices else None
    if device is None:
        return ucapi.SetupError()
    if kind == "remove":
        config.devices.remove(device_id)
        return ucapi.SetupComplete()
    return await _start_device(device.series, device.address, device.name, existing=device)


# =============================================================================
# Entry point
# =============================================================================


async def driver_setup_handler(msg: ucapi.SetupDriver) -> ucapi.SetupAction:
    """Dispatch setup messages from the remote."""
    _LOG.info("Setup message: %s", type(msg).__name__)

    if isinstance(msg, ucapi.AbortDriverSetup):
        _LOG.info("Setup aborted")
        _pending.clear()
        return ucapi.SetupError()

    if isinstance(msg, ucapi.DriverSetupRequest):
        _pending.clear()
        data = msg.setup_data or {}
        if str(data.get("address", "")).strip():
            return await _start_device(data.get("series", "TX-NR6xx"), data["address"], str(data.get("name", "")).strip())
        if msg.reconfigure and config.devices is not None and any(True for _ in config.devices.all()):
            return _action_form()
        return _device_form()

    if isinstance(msg, ucapi.UserDataResponse):
        values = msg.input_values or {}
        if "action" in values:
            return await _handle_action(str(values["action"]))
        if "address" in values:
            return await _start_device(values.get("series", "TX-NR6xx"), values["address"], str(values.get("name", "")).strip())
        if "inputs" in values or "modes" in values:
            return _save_names(values)

    _LOG.warning("Unexpected setup message: %s", type(msg).__name__)
    return ucapi.SetupError()
