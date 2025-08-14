# Hublink Scanner Module

This module provides Bluetooth Low Energy scanning functionality for discovering and managing Hublink devices.

## Features

- **Device Discovery**: Scan for Hublink devices using the custom service UUID
- **Device Management**: Connect/disconnect to discovered devices
- **Device Information**: Read device configuration and status
- **Cross-Platform**: Works on macOS (development) and Linux/Raspberry Pi (production)

## Architecture

```
modules/scanner/
├── __init__.py          # Module initialization
├── scanner.py           # Core Bluetooth scanner functionality
├── routes.py            # Flask API routes
├── templates/
│   └── scanner.html     # Frontend template
└── README.md           # This file
```

## API Endpoints

### Scanner Control
- `GET /api/scanner/status` - Get scanner status
- `POST /api/scanner/start` - Start scanning for devices
- `POST /api/scanner/stop` - Stop scanning

### Device Management
- `GET /api/scanner/devices` - Get list of discovered devices
- `GET /api/scanner/device/<address>` - Get specific device details
- `POST /api/scanner/connect/<address>` - Connect to device
- `POST /api/scanner/disconnect/<address>` - Disconnect from device
- `POST /api/scanner/disconnect-all` - Disconnect from all devices

### Testing
- `POST /api/scanner/test` - Test scanner functionality

## Hublink BLE UUIDs

The scanner specifically looks for devices with these UUIDs:

- **Service UUID**: `57617368-5501-0001-8000-00805f9b34fb`
- **Node Characteristic**: `57617368-5505-0001-8000-00805f9b34fb` (for reading device info)
- **Gateway Characteristic**: `57617368-5504-0001-8000-00805f9b34fb` (for commands)
- **Filename Characteristic**: `57617368-5502-0001-8000-00805f9b34fb` (for file operations)
- **File Transfer Characteristic**: `57617368-5503-0001-8000-00805f9b34fb` (for data transfer)

## Dependencies

- **Bleak**: Cross-platform Bluetooth Low Energy library
- **Flask**: Web framework for API routes
- **asyncio**: For async Bluetooth operations

## Installation

1. Install the required dependencies:
   ```bash
   pip install bleak
   ```

2. The module is automatically loaded by the main application if available.

## Development

### Testing the Module

Run the test script to verify the module loads correctly:

```bash
python test_scanner.py
```

### Environment Considerations

**macOS (Development)**:
- Requires Bluetooth permissions in System Preferences
- Uses Core Bluetooth framework via Bleak
- May need to grant permissions to Python/Terminal

**Linux/Raspberry Pi (Production)**:
- Uses BlueZ via Bleak
- May require running with elevated privileges for Bluetooth access
- Ensure Bluetooth service is running: `sudo systemctl start bluetooth`

### Troubleshooting

1. **Import Errors**: Make sure Bleak is installed
2. **Permission Errors**: Check Bluetooth permissions on macOS
3. **No Devices Found**: Ensure Hublink devices are nearby and advertising
4. **Connection Failures**: Check device is in range and not connected elsewhere

## Integration

The scanner module integrates seamlessly with the main hypervisor:

- **Minimal Changes**: Only adds a few lines to `app.py`
- **Optional Loading**: Gracefully handles missing dependencies
- **Clean API**: All scanner endpoints under `/api/scanner/` prefix
- **Frontend Integration**: Scanner tab in the main interface

## Future Enhancements

- File transfer operations
- Device configuration management
- Real-time device monitoring
- Batch operations for multiple devices
