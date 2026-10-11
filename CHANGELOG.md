# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.8.0] - 2026-10-11

### Added
- Learn mode (setup → "Learn listening modes & inputs"): while recording, every listening mode / input the receiver reports (e.g. switched with the original remote) is collected. Afterwards each code gets a name field (empty = hide); the learned modes can replace the list (removes modes the receiver doesn't offer) or be merged. Applied live.

## [0.7.1] - 2026-10-11

### Fixed
- The Roon & standby settings could not be reached: `driver.json` had a fixed first setup page (series / IP / name), which the Remote also shows when reconfiguring, so the setup always jumped to the names form and the menu never appeared. The first page is now an info page only (like the official Denon integration), all forms come from the driver.
- Reconfigure always shows the menu (edit names, Roon & standby, add, remove), even if an older cached `driver.json` still sends the IP page.

### Changed
- A first-time setup ends with the optional Roon page (Roon off by default, can be skipped).
- Setup start waits 1 s before answering (web configurator workaround, as in the Denon integration).

## [0.7.0] - 2026-10-11

### Added
- Roon control directly in the integration on the Remote (setup → "Roon & standby settings"), no server needed.
- Keep the Remote awake while Roon plays in the Onkyo zone: temporary, renewed standby inhibitor via the Remote's Core API (API key created once from the web configurator PIN; PIN not stored), with a minimum battery level. In the dock the Remote doesn't sleep anyway.
- Roon extension subscribes to transport zones (optional service) to detect playback; optional zone name.
- After waking up, the Roon connection is renewed like the receiver connection.
- Tests: mock Core API, Roon zones, driver on the Remote (`tests/test_remote_roon.py`).

## [0.6.0] - 2026-10-11

### Added
- Roon volume control + source control (replaces roon-extension-onkyo): own asyncio implementation of the Roon extension protocol (SOOD discovery, registration with stored token, ping/status/volume/source services), no Node.js needed.
- Docker container (`Dockerfile`, `docker-compose.yml`, `intg-onkyoavr/container.py`) with `MODE=roon` (Roon only, Remote keeps its own integration) and `MODE=full` (Remote integration + Roon, receivers stay connected).
- GitHub Actions workflow building the multi-arch image (amd64/arm64) to GHCR.
- Mock Roon Core and Roon tests (`tests/mock_roon_core.py`, `tests/test_roon.py`), run in CI.

### Fixed
- After the Remote removed all entities of a receiver, its event handlers were removed for good, so later updates were never sent again (re-adding the entities only reconnected).

## [0.5.0] - 2026-10-09

### Added
- ONKYO logo as integration icon (`custom:onkyo.png`, installed automatically with the archive) and in the README, with trademark notice (README, NOTICE).
- Select entities (dropdowns) for input source and listening mode.
- Own names for inputs and listening modes, unused ones can be hidden: editable "Code = Name" lists in the setup. Media player, dropdowns and stored activities use the same names.
- Input names and model are read from the receiver (`NRIQSTN`, models ~2016+). For configurations from 0.4.x without own names this happens automatically on connect.
- Running the setup again (reconfigure): edit names, add another receiver, remove a receiver. Entering the IP of an existing receiver updates it instead of silently doing nothing.
- Listening mode names for models from 2016 on (Dolby Atmos/Surround, DTS:X/Neural:X, DTS Virtual:X, Game-RPG/Action/Rock/Sports, AllCh Stereo, Full Mono, Pure Direct).
- Simple commands `LISTENING_MODE_MONO`, `LISTENING_MODE_STRAIGHT`, `LISTENING_MODE_DOLBY_SURR`, `LISTENING_MODE_NEURAL_X`.
- Mock receiver (`tests/mock_receiver.py`) and end-to-end test (`tests/test_e2e.py`), run in CI.

### Fixed
- Wrong input codes: PHONO sent the code of TAPE (20 instead of 22), CD/TUNER/TV-CD were shifted, BLUETOOTH and AIRPLAY were swapped (also in the simple commands `INPUT_BLUETOOTH` / `INPUT_AIRPLAY`).
- Listening mode names were the pre-2016 ones, so e.g. Dolby Surround was shown as "PLII/PLIIx MOVIE" and Game-RPG as "FILM".
- `LISTENING_MODE_FILM` / `_MUSIC` / `_GAME` now cycle through the Movie/TV, Music and Game categories (like the buttons on the Onkyo remote). Before they set fixed codes that mean something else on newer models (e.g. MUSIC -> Game-Rock).
- Re-running the setup for an existing receiver did nothing ("Device already exists").
- Remote entity state did not follow the receiver power state (the update dict was modified before it was checked).

## [0.4.3] - 2026-10-03

### Changed
- Updated ucapi from 0.5.x to 0.7 (pinned to `>=0.7.0,<0.8`).
  - `MediaType` -> `MediaContentType`, device class via `DeviceClasses.RECEIVER`.
  - Entity `command()` uses the current signature (`websocket` keyword) instead of the legacy fallback.
  - Remote entity passes `simple_commands` directly instead of patching `options` after init.
  - With newer firmware only entity types the Remote supports are announced. Older firmware gets all entities after a 5 s timeout.
- Driver creates its own event loop instead of the deprecated `asyncio.get_event_loop()`.

### Fixed
- Entity IDs stay unchanged (`EntityTypes.MEDIA_PLAYER.onkyo_<id>`). With ucapi 0.6+ they would have become `media_player.onkyo_<id>`, and existing activities would have lost their Onkyo entities.

## [0.4.2] - 2026-10-02

### Fixed
- Driver crashed on startup when built with ucapi 0.6.0+ (`MediaType` removed) -> setup failed with "connection refused". ucapi is now pinned to 0.5.x.
- Receiver was not connected after setup / on entity subscription: entity IDs look like `EntityTypes.MEDIA_PLAYER.onkyo_<id>` on Python 3.11, which `avr_from_entity_id` could not parse.
- Connection to the receiver lost after the Remote woke up from standby (firmware 2.10.2+ reconnects integrations immediately after WiFi wake-up).
- Concurrent connect calls (CONNECT, EXIT_STANDBY, SUBSCRIBE_ENTITIES) could open parallel connections whose listen tasks read the same stream and killed the connection.
- intg-onkyoavr/driver.py was accidentally overwritten with driver.json content in 0.4.1 and has been restored.

### Added
- Automatic reconnect with backoff (1, 2, 5, 10, 30 s).
- Heartbeat (PWRQSTN after 30 s without traffic, 5 s answer timeout) to detect half-open connections.
- TCP keepalive on the eISCP socket.
- On EXIT_STANDBY the connection is always replaced by a fresh one.

## [0.1.0] - 2025-01-19

### Added
- Initial release
- Basic Onkyo AVR control via eISCP protocol
- Automatic network discovery of receivers
- Manual IP configuration
- Power control (on/off)
- Volume control (0-100%, up/down, mute)
- Input source selection
- Real-time status updates

### Supported Features
- Power: On, Off, Toggle
- Volume: Set, Up, Down
- Mute: Toggle, Mute, Unmute
- Source: Select from available inputs

### Known Limitations
- No multi-zone support yet
- Limited to main zone only
- No sound mode selection yet

[Unreleased]: https://github.com/quintz/integration-onkyoavr/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/quintz/integration-onkyoavr/releases/tag/v0.1.0
