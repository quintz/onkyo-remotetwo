<p align="center"><img src="assets/onkyo-logo.png" alt="ONKYO" width="300"></p>

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
- **Learn mode** (0.8.0+): step through the modes with the original remote, the integration records the codes your receiver really uses
- Input names are read from the receiver itself (models with network info support, ~2016+)
- Real-time status updates via eISCP protocol
- **Roon zone volume control** (0.6.0+): the receiver appears in Roon as *Volume Control* and *Source Control* (volume, mute, power on + input switch, standby), replacing a separate Roon extension. See [Roon zone volume control](#roon-zone-volume-control)
  - **Integrated in the Remote integration** (0.7.0+): no server needed, optionally keeps the Remote awake while Roon plays
  - **Standalone Docker container** (0.6.0+): runs on a server (e.g. Proxmox), Roon control independent of the Remote

## Supported Receivers

This integration should work with most Onkyo receivers that support network control via eISCP protocol, including:

- TX-NR series (e.g., TX-NR696, TX-NR686, TX-NR676)
- TX-RZ series
- And many others with network capabilities

## Requirements

- Onkyo receiver with network connection
- Network Control enabled on the receiver
- Same network as Remote Two/3
- Optional for Roon: a Roon Core in the same network; for the standalone variant a Docker host (e.g. Proxmox LXC/VM)

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
3. Enter the IP address of your receiver and give it a name
4. Check the names of inputs and listening modes (see below)
5. Optional: enable Roon control (see [Roon zone volume control](#roon-zone-volume-control)), or continue without it

**Change settings later:** open the integration in the web configurator and run the setup again (*Configure*). A menu offers:

- *Edit names: …* (inputs and listening modes of a receiver)
- *Learn listening modes & inputs: …* (record them from the receiver, see below)
- *Roon & standby settings*
- *Add another receiver* / *Remove: …*

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

### Learn listening modes & inputs (0.8.0+)

Which listening modes a receiver offers (and which codes it uses for them) differs between models and firmware versions. Instead of guessing, let the integration learn them from your receiver:

1. Run the setup again → **Learn listening modes & inputs: <receiver>**
2. Recording starts. Use the **original Onkyo remote** (or the buttons on the receiver) and step through all modes you use, e.g. press *Movie/TV*, *Music*, *Game*, *Stereo*, *Direct*, *Pure Audio* repeatedly, waiting a moment after each step. You can switch inputs as well. Press **Next**.
3. Every code the receiver reported gets a name field, prefilled with the known name. Enter your own name, or leave it **empty to hide** the mode.
4. Choose whether the learned modes **replace** the list (removes modes your receiver doesn't offer) or are **added**. Inputs are added/renamed by default. Tick *Continue learning* to record more.

The dropdowns and the media player use the new lists immediately. Some modes only appear with a matching signal (e.g. Dolby Atmos only with Atmos content); play something in that format to learn them.

## Supported Commands

- Power On/Off/Toggle
- Volume Up/Down/Set (0-80)
- Mute/Unmute/Toggle
- Input Source Selection
- Sound Mode Selection
- D-Pad Navigation
- Playback Controls (Play/Pause/Stop/Next/Previous)

## Roon zone volume control

The integration can offer the receiver to **Roon**. In the Roon zone you then get:

| Roon function | What happens on the receiver |
|---|---|
| Volume slider, +/- | Master volume in receiver steps (0–80, upper limit configurable) |
| Mute | Mute on/off/toggle |
| Source control "convenience switch" (when playback starts) | Power on, switch to the Roon input |
| Source control "standby" | Power off |
| Zone status | Shows whether the receiver is on the Roon input, on another input or in standby |

Changes made on the receiver or with the Remote (volume, mute, power, input) show up in Roon immediately. It replaces [roon-extension-onkyo](https://github.com/quintz/roon-extension-onkyo); disable the old extension so there aren't two Onkyo controls.

### Which variant?

| | **Integrated** (on the Remote) | **Standalone Docker**, `MODE=roon` | **Docker**, `MODE=full` |
|---|---|---|---|
| Extra server | none | Docker host | Docker host |
| Roon control available | while the Remote is awake (always in the dock) | always | always |
| Remote control without the server | yes | yes (own integration on the Remote) | no |
| Configuration | setup → *Roon & standby settings* | environment variables | environment variables |
| Keep Remote awake while Roon plays | yes (optional) | not needed | not needed |

- Remote mostly in the dock → **Integrated** is enough.
- Roon control must work no matter where the Remote is → **Standalone Docker** (`MODE=roon`).
- Run only one variant with Roon enabled at a time.

## Roon directly on the Remote (0.7.0+)

Roon control can also run **inside the integration on the Remote**, no extra server needed:

1. Run the integration setup again → **Roon & standby settings**
2. Enable Roon control, choose the input for Roon and the max. volume
3. Optional: **Keep the Remote awake while Roon plays**. Enter the **web configurator PIN** once (shown on the Remote under Settings → Web configurator). The integration creates an API key with it; the PIN is not stored.
4. In Roon: Settings → Extensions → enable "Onkyo AVR (Remote Two integration)", then choose it as Volume / Source Control in the zone

How it behaves:

- **In the dock** the Remote doesn't go to standby, so Roon control is always available.
- **On battery**, while Roon plays in the zone using the Onkyo, the integration sets a *temporary* standby inhibitor (5 min) and renews it every 2 min. If the integration stops or the Remote loses the connection, the inhibitor simply expires, so the Remote can't be kept awake forever. Below the configured battery level it isn't set.
- **If the Remote is already asleep** when you start Roon (e.g. from the phone), Roon can't reach it; volume control appears as soon as the Remote wakes up. If you need Roon control independent of the Remote, use the container below.
- The Remote's Core API is reached at `http://127.0.0.1` by default. If the setup reports it as not reachable, enter the Remote's IP address in the field *Remote Core API*.

## Standalone Docker container (0.6.0+)

The same code runs as a **standalone Docker container** (e.g. on Proxmox), independent of the Remote. It offers the receiver to Roon with all [Roon zone functions](#roon-zone-volume-control) and shows its status in Roon → Settings → Extensions. The image is multi-arch (amd64/arm64) and is built automatically to `ghcr.io/quintz/onkyo-remotetwo`.

### Modes

| `MODE` | What runs in the container | Remote uses |
|---|---|---|
| `roon` (default, **recommended**) | Roon bridge only | the integration **installed on the Remote** |
| `full` | Remote integration (found via mDNS) **and** Roon | the integration **in the container** |

**Why `roon` is recommended (fallback):** with `MODE=roon` the Remote never depends on the container. If Proxmox is down, the Remote still controls the receiver; only Roon loses its volume control. The Remote has no automatic failover between two integrations: a second integration creates its own entities, and activities point to exactly one of them. So the robust split is "Remote → own integration, Roon → container".

`MODE=full` saves the second receiver connection and the install on the Remote, but if the container is down, the Remote can't control the receiver either. In this mode receivers stay connected permanently (no disconnect on Remote standby).

### Setup (Proxmox: Docker in an LXC with `nesting=1`, or a VM)

```sh
mkdir onkyo && cd onkyo
curl -O https://raw.githubusercontent.com/quintz/onkyo-remotetwo/main/docker-compose.yml
# edit ONKYO_HOST, ROON_SOURCE
docker compose up -d
```

Then in Roon: **Settings → Extensions → "Onkyo AVR (Remote Two integration)" → Enable**, and in the zone: **Device Setup → Volume Control / Source Control → Onkyo**. Disable the old Node.js extension, otherwise there are two Onkyo controls.

| Variable | Default | Meaning |
|---|---|---|
| `MODE` | `roon` | `roon` or `full` |
| `ONKYO_HOST` | – | receiver IP (`MODE=roon`) |
| `ONKYO_NAME` | `Onkyo` | name in Roon |
| `ROON_SOURCE` | – | input Roon switches to: code (`11`) or name (`STRM BOX`, `BD/DVD`, `NET`, own names) |
| `ROON_VOLUME_MAX` | `80` | upper limit of the Roon volume slider |
| `ROON_VOLUME_STEP` | `1` | step for +/- in Roon |
| `ROON_CORE` | auto | `host[:port]` if discovery doesn't find the core |
| `DATA_DIR` | `/data` | Roon token, UC config (`MODE=full`) |
| `LOG_LEVEL` | `INFO` | `DEBUG` for details |

Host networking (`network_mode: host`) is required for Roon discovery and mDNS. The image is built by GitHub Actions for amd64 and arm64: `ghcr.io/quintz/onkyo-remotetwo`.

## Trademark notice

ONKYO® and the ONKYO logo are registered trademarks of Onkyo and/or their respective owner. The logo is used only to identify the supported receivers (as the integration icon in the Remote and in this README). This project is an independent community project and is not affiliated with, endorsed or sponsored by Onkyo. The logo files in `assets/` are **not** covered by the project license.

*ONKYO® und das ONKYO-Logo sind eingetragene Marken von Onkyo bzw. des jeweiligen Rechteinhabers. Das Logo dient nur dazu, die unterstützten Receiver zu kennzeichnen. Dieses Projekt ist ein unabhängiges Community-Projekt und steht in keiner Verbindung zu Onkyo. Die Logo-Dateien in `assets/` fallen **nicht** unter die Projektlizenz.*

## License

This project is licensed under the Mozilla Public License 2.0 - see [LICENSE](LICENSE) file for details. This does not apply to the ONKYO logo, see [Trademark notice](#trademark-notice) and [NOTICE](NOTICE).

## Credits

- Structure inspired by the [Denon AVR integration](https://github.com/unfoldedcircle/integration-denonavr) by Unfolded Circle.
- eISCP protocol implementation based on Onkyo documentation and https://github.com/miracle2k/onkyo-eiscp
- Roon extension protocol based on [node-roon-api](https://github.com/RoonLabs/node-roon-api) by Roon Labs; behaviour modelled after [roon-extension-onkyo](https://github.com/quintz/roon-extension-onkyo)

## Author

Created by Quirin ([@quintz](https://github.com/quintz))
