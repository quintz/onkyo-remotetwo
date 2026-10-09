# Onkyo AVR integration for Remote Two/3

Control your Onkyo AV Receivers with the Unfolded Circle Remote Two/3.

This integration uses the eISCP (Ethernet Integra Serial Control Protocol) to communicate with Onkyo receivers over the network.

## Features

- Manual configuration by IP address
- Power control (on/off)
- Volume control (including mute)
- Input source selection
- Sound mode / listening mode selection
- Dropdown entities for input and listening mode (select entities, 0.5.0+)
- Own names for inputs and listening modes, hide unused ones (0.5.0+)
- Input names are read from the receiver itself (models with network info support, ~2016+)
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

## Inputs, listening modes and own names (0.5.0+)

Per receiver the integration creates two dropdowns in addition to the media player and remote:

| Entity | Content |
|---|---|
| `<Name> Input` / `Eingang` | Inputs of the receiver |
| `<Name> Listening mode` / `Klangmodus` | Listening modes |

After entering the IP in the setup, the integration asks the receiver for its info (`NRIQSTN`). Newer models (e.g. TX-NR686) report their model and the inputs with the names you set on the receiver. The next setup page shows two editable lists, one line per entry:

```
10 = Apple TV
02 = PlayStation
2E = BLUETOOTH
```

- **Delete a line** to hide the input/mode in the dropdowns and the media player.
- **Change the name** after `=` to rename it.
- Standard names work instead of codes, e.g. `BD/DVD = Apple TV`. A line with only a code uses the standard name.
- Leave a list **empty** for automatic (inputs from the receiver, standard listening modes).
- The page lists all other codes, so you can add inputs or modes that are missing.

**Listening mode names:** Onkyo reused the codes. Models from 2016 on show *Dolby Atmos/Surround* (80), *DTS:X/Neural:X* (82), *Game-RPG/Action/Rock/Sports* (03/05/06/0E). Older models show *PLII*, *Neo:6*, *Film*, *Musical* for the same codes. The setup picks the right set automatically from the receiver's year; you can switch it on the names page.

**Change names later:** run the setup of the integration again. You can then edit the names of a receiver, add another receiver or remove one. Changes apply immediately, without reconnecting.

Activities created with older versions keep working: the old names (e.g. `NETWORK`, `PLII/PLIIx MOVIE`) are still accepted.

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
- eISCP protocol implementation based on Onkyo documentation and https://github.com/miracle2k/onkyo-eiscp

## Author

Created by Quirin ([@quintz](https://github.com/quintz))
