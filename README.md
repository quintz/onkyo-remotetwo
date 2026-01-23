# Onkyo AVR integration for Remote Two/3

Control your Onkyo AV Receivers with the Unfolded Circle Remote Two/3.

This integration uses the eISCP (Ethernet Integra Serial Control Protocol) to communicate with Onkyo receivers over the network.

## Features

- Manual configuration by IP address
- Power control (on/off)
- Volume control (including mute)
- Input source selection
- Sound mode / listening mode selection
- Real-time status updates via eISCP protocol

## Supported Receivers

This integration should work with most Onkyo receivers that support network control via eISCP protocol, including:

- TX-NR series (e.g., TX-NR696, TX-NR686, TX-NR676)
- TX-RZ series
- And many others with network capabilities

## Requirements

- Onkyo receiver with network connection
- Network Control enabled on the receiver
- Same network as Remote Two/3

## Installation

### From Release

1. Download the latest `.tar.gz` file from [Releases](https://github.com/quintz/integration-onkyoavr/releases)
2. Open your Remote Two/3 web configurator
3. Go to Settings → Integrations
4. Click "Install" and upload the `.tar.gz` file

### From Source

Build the integration package using GitHub Actions or locally with Docker.

## Setup

1. Ensure your Onkyo receiver is powered on and connected to your network
2. Add the Onkyo AVR integration in Remote Two/3
3. Enter the IP address of your receiver
4. Give it a name and complete setup

If setup doesn't work:
- Ensure the receiver's Network Control is enabled (set to "Always On")
- Check that the receiver is on the same network/VLAN
- Verify the IP address is correct

## Supported Commands

- Power On/Off/Toggle
- Volume Up/Down/Set (0-80)
- Mute/Unmute/Toggle
- Input Source Selection
- Sound Mode Selection
- D-Pad Navigation
- Playback Controls (Play/Pause/Stop/Next/Previous)

## License

This project is licensed under the Mozilla Public License 2.0 - see [LICENSE](LICENSE) file for details.

## Credits

- Structure inspired by the [Denon AVR integration](https://github.com/unfoldedcircle/integration-denonavr) by Unfolded Circle.
- eISCP protocol implementation based on Onkyo documentation.

## Author

Vibe coded by quintz via Claude Code (Because I cannot code and desperetly wanted an Onkyo Integration) ([@quintz](https://github.com/quintz))
