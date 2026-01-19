# Onkyo AVR integration for Remote Two/3

Control your Onkyo AV Receivers with the Unfolded Circle Remote Two/3.

This integration uses the eISCP (Ethernet Integra Serial Control Protocol) to communicate with Onkyo receivers over the network.

## Features

- Automatic network discovery of Onkyo receivers
- Manual configuration by IP address
- Power control (on/off)
- Volume control (including mute)
- Input source selection
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

This integration is designed to be installed as a custom integration on your Remote Two/3.

### From Release

1. Download the latest `.tar.gz` file from [Releases](https://github.com/quintz/integration-onkyoavr/releases)
2. Open your Remote Two/3 web configurator
3. Go to Settings → Integrations
4. Click "Install" and upload the `.tar.gz` file

### From Source

Build the integration package:

```bash
docker run --rm --name builder \
    --platform=linux/arm64 \
    --user=$(id -u):$(id -g) \
    -v "$PWD":/workspace \
    docker.io/unfoldedcircle/r2-pyinstaller:3.11.13 \
    bash -c \
      "PYTHON_VERSION=\$(python --version | cut -d' ' -f2 | cut -d. -f1,2) && \
      python -m pip install --user -r requirements.txt && \
      PYTHONPATH=~/.local/lib/python\${PYTHON_VERSION}/site-packages:\$PYTHONPATH pyinstaller --clean --onedir --name driver -y \
        intg-onkyoavr/driver.py"
```

## Setup

1. Ensure your Onkyo receiver is powered on and connected to your network
2. Add the Onkyo AVR integration in Remote Two/3
3. The integration will automatically discover receivers on your network
4. Select your receiver from the list
5. Give it a name and complete setup

If automatic discovery doesn't find your receiver:
- Use manual setup with the receiver's IP address
- Ensure the receiver's Network Control is enabled
- Check that the receiver is on the same network/VLAN

## Supported Commands

- Power On/Off
- Volume Up/Down
- Volume Set (0-100%)
- Mute/Unmute
- Input Source Selection
- Toggle Power

## Configuration

The integration stores device configuration in `config.json` in the integration's data directory.

## Development

### Requirements

- Python 3.11+
- Docker (for building distribution)

### Local Testing

```bash
pip3 install -r requirements.txt
python3 intg-onkyoavr/driver.py
```

## License

This project is licensed under the Mozilla Public License 2.0 - see [LICENSE](LICENSE) file for details.

## Credits

Structure and approach inspired by the [Denon AVR integration](https://github.com/unfoldedcircle/integration-denonavr) by Unfolded Circle.
