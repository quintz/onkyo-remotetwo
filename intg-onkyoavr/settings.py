"""
Integration-wide settings (Roon on the Remote, keep awake), stored in
``<config dir>/settings.json``. Set in the setup ("Roon & Standby").

:copyright: (c) 2026 by Quirin.
:license: Mozilla Public License Version 2.0, see LICENSE for more details.
"""

from __future__ import annotations

import dataclasses
import json
import logging
import os
from dataclasses import dataclass

_LOG = logging.getLogger(__name__)


@dataclass
class IntegrationSettings:
    """Settings for Roon and the standby behaviour."""

    roon_enabled: bool = False
    roon_source: str = ""  # input code Roon switches to ("" = don't switch)
    roon_volume_max: int = 80
    roon_zone: str = ""  # zone to watch for playback ("" = zones using our source control)
    roon_core: str = ""  # host[:port] of the Roon Core ("" = discovery)
    keep_awake: bool = True  # keep the Remote awake while Roon plays
    min_battery: int = 30  # ... but not below this battery level (on battery)
    core_api_url: str = "http://127.0.0.1"  # the Remote's own Core API
    core_api_key: str = ""


def _path(config_dir: str) -> str:
    return os.path.join(config_dir, "settings.json")


def load(config_dir: str) -> IntegrationSettings:
    """Load settings (defaults if the file doesn't exist)."""
    try:
        with open(_path(config_dir), encoding="utf-8") as f:
            data = json.load(f)
        known = {f.name for f in dataclasses.fields(IntegrationSettings)}
        return IntegrationSettings(**{k: v for k, v in data.items() if k in known})
    except FileNotFoundError:
        return IntegrationSettings()
    except (OSError, ValueError, TypeError) as e:
        _LOG.error("Invalid settings.json, using defaults: %s", e)
        return IntegrationSettings()


def save(config_dir: str, settings: IntegrationSettings) -> None:
    """Persist settings."""
    os.makedirs(config_dir, exist_ok=True)
    with open(_path(config_dir), "w", encoding="utf-8") as f:
        json.dump(dataclasses.asdict(settings), f, indent=2)


def roon_settings(s: IntegrationSettings):
    """Convert to roon_bridge.RoonSettings."""
    from roon_bridge import RoonSettings  # noqa: PLC0415

    core = (s.roon_core or "").strip()
    host, _, port = core.partition(":")
    return RoonSettings(
        enabled=s.roon_enabled,
        core_host=host or None,
        core_port=int(port) if port.isdigit() else None,
        source=s.roon_source,
        volume_max=max(1, min(80, int(s.roon_volume_max or 80))),
        zone=s.roon_zone,
    )
