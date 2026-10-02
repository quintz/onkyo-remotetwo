# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.2] - 2026-10-02

### Fixed
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
