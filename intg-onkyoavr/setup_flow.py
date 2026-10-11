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

import asyncio
import logging
from typing import Any, Awaitable, Callable

import avr
import config
import names
import settings as integration_settings
import ucapi
from power import CoreApi, CoreApiError
from config import AvrDevice
from const import RECEIVER_SERIES

_LOG = logging.getLogger(__name__)

# Provides receiver info for an address. The driver replaces this so a running
# connection is reused instead of opening a second one.
receiver_info_provider: Callable[[str], Awaitable[names.ReceiverInfo | None]] = avr.fetch_receiver_info

# (get_settings, apply_settings coroutine, running_in_container) - set by the driver
settings_hooks: tuple | None = None

# Step 1 data kept until the names form is submitted.
_pending: dict[str, Any] = {}
# Current page ("device", "names", "roon", "action") - lets us finish pages whose
# submitted values carry no input fields (e.g. the info-only page in the container).
_step = ""

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
    items.append({"id": "roon", "label": _text("Roon & standby settings", "Roon- & Standby-Einstellungen")})
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
    is_new = not config.devices.contains(device.id)
    config.devices.add_or_update(device)
    _LOG.info("Saved %s: %d inputs, %d listening modes", device.id, len(inputs), len(modes))
    if is_new and settings_hooks is not None:
        # first setup: offer Roon right away (optional, can be skipped)
        return _roon_form(first_setup=True)
    return ucapi.SetupComplete()


# =============================================================================
# Roon & standby settings
# =============================================================================


def _roon_form(error: str | None = None, values: dict[str, Any] | None = None, first_setup: bool = False):
    """Roon on the Remote + keep awake while Roon plays."""
    global _step
    _step = "roon"
    get_settings, _, in_container = settings_hooks
    s = get_settings()
    v = values or {}
    settings: list[dict[str, Any]] = []
    if error:
        settings.append(_label("error", _text("Error", "Fehler"), _text(error)))
    if in_container:
        settings.append(
            _label(
                "container",
                _text("Container"),
                _text(
                    "This integration runs in a container: Roon is configured with environment variables (ROON_*).",
                    "Die Integration läuft im Container: Roon wird dort über Umgebungsvariablen (ROON_*) eingestellt.",
                ),
            )
        )
        return ucapi.RequestUserInput(_text("Roon & standby", "Roon & Standby"), settings)

    if first_setup:
        settings.append(
            _label(
                "optional",
                _text("Optional"),
                _text(
                    "The receiver is set up. If you use Roon, you can enable Roon control here - or just continue "
                    "without it. You find this page later in the setup under \"Roon & standby settings\".",
                    "Der Receiver ist eingerichtet. Wenn du Roon nutzt, kannst du hier die Roon-Steuerung aktivieren – "
                    "oder einfach ohne weiter. Diese Seite findest du später im Setup unter „Roon- & Standby-Einstellungen“.",
                ),
            )
        )
    settings.append(
        _label(
            "info",
            _text("Roon"),
            _text(
                "Offers the receiver to Roon as volume and source control (enable the extension in Roon → Settings → "
                "Extensions). Works while the Remote is awake - in the dock it doesn't sleep. "
                "Optionally the Remote is kept awake while Roon plays.",
                "Stellt den Receiver in Roon als Lautstärke- und Quellensteuerung bereit (Extension in Roon → Einstellungen → "
                "Erweiterungen aktivieren). Funktioniert, solange die Remote wach ist – im Dock schläft sie nicht. "
                "Optional bleibt die Remote wach, solange Roon spielt.",
            ),
        )
    )
    settings.append({"id": "roon_enabled", "label": _text("Enable Roon control", "Roon-Steuerung aktivieren"),
                     "field": {"checkbox": {"value": bool(v.get("roon_enabled", s.roon_enabled))}}})

    # input for Roon: inputs of the first receiver
    items = [{"id": "", "label": _text("(don't switch input)", "(Eingang nicht umschalten)")}]
    device = next(iter(config.devices.all()), None) if config.devices else None
    entries = list(device.inputs) if device and device.inputs else names.default_inputs()
    for code, name in entries:
        items.append({"id": code, "label": _text(f"{name} ({code})")})
    current = str(v.get("roon_source", s.roon_source))
    if current and current not in [i["id"] for i in items]:
        items.append({"id": current, "label": _text(current)})
    settings.append({"id": "roon_source", "label": _text("Input for Roon", "Eingang für Roon"),
                     "field": {"dropdown": {"value": current, "items": items}}})
    settings.append({"id": "roon_volume_max", "label": _text("Max. volume from Roon (0-80)", "Max. Lautstärke aus Roon (0-80)"),
                     "field": {"number": {"value": int(v.get("roon_volume_max", s.roon_volume_max)), "min": 1, "max": 80}}})
    settings.append({"id": "keep_awake", "label": _text("Keep the Remote awake while Roon plays", "Remote wach halten, solange Roon spielt"),
                     "field": {"checkbox": {"value": bool(v.get("keep_awake", s.keep_awake))}}})
    settings.append({"id": "min_battery", "label": _text("…but only above battery level (%)", "…aber nur ab Akkustand (%)"),
                     "field": {"number": {"value": int(v.get("min_battery", s.min_battery)), "min": 0, "max": 100}}})
    key_state = (
        _text("An API key exists. Only enter the PIN to create a new one.", "Ein API-Key ist vorhanden. PIN nur eingeben, um einen neuen anzulegen.")
        if s.core_api_key
        else _text(
            "Needed once to keep the Remote awake: the PIN is shown on the Remote under Settings → Web configurator. "
            "The integration creates an API key with it; the PIN itself is not stored.",
            "Einmalig nötig, um die Remote wach zu halten: Die PIN steht auf der Remote unter Einstellungen → Web-Configurator. "
            "Die Integration legt damit einen API-Key an, die PIN selbst wird nicht gespeichert.",
        )
    )
    settings.append(_label("pin_info", _text("Web configurator PIN", "Web-Configurator-PIN"), key_state))
    settings.append({"id": "pin", "label": _text("Web configurator PIN", "Web-Configurator-PIN"), "field": {"password": {"value": ""}}})
    settings.append({"id": "roon_zone", "label": _text("Roon zone (optional, default: zones using the Onkyo)", "Roon-Zone (optional, Standard: Zonen mit dem Onkyo)"),
                     "field": {"text": {"value": str(v.get("roon_zone", s.roon_zone))}}})
    settings.append({"id": "roon_core", "label": _text("Roon Core address (optional, default: auto)", "Roon-Core-Adresse (optional, Standard: automatisch)"),
                     "field": {"text": {"value": str(v.get("roon_core", s.roon_core))}}})
    settings.append({"id": "core_api_url", "label": _text("Remote Core API (advanced)", "Core-API der Remote (Experten)"),
                     "field": {"text": {"value": str(v.get("core_api_url", s.core_api_url))}}})
    return ucapi.RequestUserInput(_text("Roon & standby", "Roon & Standby"), settings)


def _to_int(value: Any, default: int) -> int:
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return default


def _host_port(raw: str) -> str:
    """'http://10.0.0.5:9330/' -> '10.0.0.5:9330' (port kept, unlike normalize_address)."""
    text = raw.strip()
    if "://" in text:
        text = text.split("://", 1)[1]
    return text.split("/", 1)[0].strip()


def _bool(value: Any) -> bool:
    return str(value).strip().lower() in ("true", "1", "yes", "on")


async def _save_roon(values: dict[str, Any]):
    global _step
    _step = ""
    get_settings, apply_settings, in_container = settings_hooks
    if in_container:
        return ucapi.SetupComplete()
    old = get_settings()
    new = integration_settings.IntegrationSettings(
        roon_enabled=_bool(values.get("roon_enabled", False)),
        roon_source=str(values.get("roon_source", "") or "").strip().upper(),
        roon_volume_max=max(1, min(80, _to_int(values.get("roon_volume_max"), 80))),
        roon_zone=str(values.get("roon_zone", "") or "").strip(),
        roon_core=_host_port(str(values.get("roon_core", "") or "")),
        keep_awake=_bool(values.get("keep_awake", False)),
        min_battery=max(0, min(100, _to_int(values.get("min_battery"), 30))),
        core_api_url=str(values.get("core_api_url", "") or "").strip() or "http://127.0.0.1",
        core_api_key=old.core_api_key if str(values.get("core_api_url", "") or "").strip() in ("", old.core_api_url) else "",
    )
    pin = str(values.get("pin", "") or "").strip()
    if new.roon_enabled and new.keep_awake and (pin or not new.core_api_key):
        if not pin:
            return _roon_form(
                "Zum Wachhalten wird einmalig die Web-Configurator-PIN gebraucht (oder „wach halten“ abwählen). / "
                "The web configurator PIN is needed once to keep the Remote awake (or untick keep awake).",
                values,
            )
        try:
            api = CoreApi(new.core_api_url)
            new.core_api_key = await api.create_api_key(pin)
            await api.battery()  # proves the key works
        except (CoreApiError, ValueError) as e:
            msg = "PIN falsch / wrong PIN" if getattr(e, "status", None) == 401 else str(e)
            return _roon_form(f"Core-API der Remote: {msg}", values)
    await apply_settings(new)
    _LOG.info("Roon settings saved (enabled: %s, keep awake: %s)", new.roon_enabled, new.keep_awake)
    return ucapi.SetupComplete()


async def _handle_action(action: str):
    if action == "roon":
        return _roon_form()
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

    global _step
    if isinstance(msg, ucapi.DriverSetupRequest):
        _pending.clear()
        _step = ""
        data = msg.setup_data or {}
        _LOG.info("Setup start (reconfigure=%s, setup_data=%s)", msg.reconfigure, sorted(data))
        # Workaround (as in the official Denon integration): the web configurator
        # sometimes misses a response sent immediately.
        await asyncio.sleep(1)
        has_devices = config.devices is not None and any(True for _ in config.devices.all())
        if msg.reconfigure and has_devices:
            # Always the menu - also if an old driver.json still sends the IP page first.
            return _action_form()
        if str(data.get("address", "")).strip():
            # driver.json up to 0.7.0 had series/address/name on the first page
            return await _start_device(data.get("series", "TX-NR6xx"), data["address"], str(data.get("name", "")).strip())
        return _device_form()

    if isinstance(msg, ucapi.UserDataResponse):
        values = msg.input_values or {}
        if "action" in values:
            return await _handle_action(str(values["action"]))
        if "address" in values:
            return await _start_device(values.get("series", "TX-NR6xx"), values["address"], str(values.get("name", "")).strip())
        if "inputs" in values or "modes" in values:
            return _save_names(values)
        if "roon_enabled" in values or _step == "roon":
            return await _save_roon(values)

    _LOG.warning("Unexpected setup message: %s", type(msg).__name__)
    return ucapi.SetupError()
