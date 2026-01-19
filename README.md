# Onkyo AVR Integration for Unfolded Circle Remote Two

Integration for Onkyo AV Receivers using the eISCP protocol.

## Features

✅ Automatic network discovery  
✅ Power control (On/Off)  
✅ Volume control (0-100%)  
✅ Mute control  
✅ Input source selection  
✅ Real-time status updates  

## Supported Models

All Onkyo receivers with eISCP protocol support, including:

- TX-NR696
- TX-NR686  
- TX-RZ50
- And many more eISCP-compatible models

## Installation

### Prerequisites

- Unfolded Circle Remote Two with firmware v1.9.0+
- Onkyo receiver on the same network
- Receiver's "Network Control" must be set to "Always On"

### Steps

1. **Download** the latest release: `ucr2-intg-onkyo-X.X.X.tar.gz`

2. **Open Remote web configurator**:
   ```
   http://[YOUR-REMOTE-IP]
   ```

3. **Install integration**:
   - Settings → Integrations → Install
   - Upload the .tar.gz file
   - Wait for installation to complete

4. **Setup receiver**:
   - Integration will automatically discover your receiver
   - Select your receiver from the list
   - Give it a name
   - Done!

## Building from Source

### Requirements

- Docker
- Linux or macOS (for ARM64 build)

### Build

```bash
./build.sh
```

This will:
1. Build Python binary with PyInstaller
2. Create proper directory structure
3. Package as .tar.gz

## Development

### Local Testing

```bash
# Install dependencies
pip install -r requirements.txt

# Run integration
UC_CONFIG_HOME=./config python intg-onkyo/driver.py
```

### Structure

```
onkyo-integration/
├── intg-onkyo/          # Python source
│   ├── driver.py        # Main driver
│   ├── receiver.py      # eISCP protocol
│   ├── media_player.py  # Media player entity
│   └── const.py         # Constants
├── driver.json          # Integration metadata
├── build.sh             # Build script
└── requirements.txt     # Dependencies
```

## Troubleshooting

### Receiver not found

1. Ensure receiver is powered on
2. Check "Network Control" is "Always On"
3. Verify same network/VLAN
4. Try manual IP configuration

### Cannot connect

1. Check receiver IP address
2. Verify port 60128 is accessible
3. Restart receiver
4. Check integration logs

## License

MIT License

## Credits

Created by Quirin for the Unfolded Circle community.

## Support

- GitHub Issues: Bug reports & features
- Unfolded Circle Forum: Community support
