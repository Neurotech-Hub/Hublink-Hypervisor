# Hublink.cloud™ Hypervisor

A clean, minimal Flask web application for monitoring and controlling Hublink Docker containers on Raspberry Pi 5 or development machines. Features intelligent auto-fix capabilities for common issues and comprehensive system monitoring.

## Prerequisites

- Python 3.11+
- Docker and Docker Compose (for containerized deployment)
- Hublink containers running from `/opt/hublink` directory

## Development Setup

### Local Development Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Neurotech-Hub/Hublink-Hypervisor.git
   cd Hublink-Hypervisor
   ```

2. **Create and activate virtual environment**:
   ```bash
   # Create virtual environment
   python3 -m venv venv
   
   # Activate virtual environment
   # On macOS/Linux:
   source venv/bin/activate
   # On Windows:
   # venv\Scripts\activate
   ```

3. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   
   # Optional: Upgrade pip to latest version
   pip install --upgrade pip
   ```

4. **Ensure Hublink containers are set up**:
   - Verify that your Hublink Docker containers are configured in `/opt/hublink`
   - The app will automatically detect `docker-compose.yml` or `docker-compose.macos.yml`

5. **Start the application**:
   ```bash
   # Make sure your virtual environment is activated
   source venv/bin/activate
   
   # Start the application
   python app.py
   ```

The application will start on `http://localhost:8081`

## Project Structure

```
Hublink-Hypervisor/
├── app.py                           # Main Flask application
├── requirements.txt                 # Python dependencies
├── start.sh                        # Development startup script
├── Dockerfile                      # Docker container definition
├── docker-compose.yml              # Docker Compose configuration
├── templates/
│   └── index.html                  # Main dashboard template
└── static/
    ├── css/
    │   └── style.css               # Custom CSS styles
    └── js/
        └── app.js                  # Frontend JavaScript
```

## Key Components

1. **HublinkManager**: Handles Docker container operations and status monitoring
2. **InternetChecker**: Checks internet connectivity for both app and containers
3. **AutoFixManager**: Intelligent issue detection and automatic resolution
4. **BluetoothScanner**: Bluetooth Low Energy device discovery and management
5. **Frontend**: Clean, responsive UI with real-time updates
6. **API**: RESTful endpoints for status and control operations

## API Endpoints

### Health Check
```bash
GET /api/health
```
Returns basic health status of the hypervisor.

### System Status
```bash
GET /api/status
```
Returns comprehensive system status including:
- Container state
- Internet connectivity
- Error details
- Hublink API status
- Auto-fix status and recent actions

### Container Management
```bash
POST /api/containers/start
POST /api/containers/stop
POST /api/containers/restart
```
Control Hublink container operations.

### Container Information
```bash
GET /api/containers
GET /api/containers/state
```
Get detailed or simplified container information.

### Auto-Fix Management
```bash
GET /api/autofix/status
```
Get current auto-fix configuration and status.

```bash
POST /api/autofix/toggle
```
Enable or disable auto-fix functionality.

### Container Logs
```bash
GET /api/logs
```
Get recent container logs.

### Bluetooth Scanner
```bash
GET /api/scanner/status
GET /api/scanner/devices
GET /api/scanner/commands
POST /api/scanner/start
POST /api/scanner/stop
POST /api/scanner/connect/<address>
POST /api/scanner/disconnect/<address>
POST /api/scanner/read-node/<address>
POST /api/scanner/write-gateway/<address>
```
Bluetooth Low Energy device scanning, connection, and communication.

## Configuration

### Environment Variables

The application uses the following default configuration:

- `HUBLINK_PATH`: `/opt/hublink` (path to Hublink containers)
- `DOCKER_COMPOSE_FILE`: `docker-compose.yml` (standard compose file)
- `DOCKER_COMPOSE_MAC_FILE`: `docker-compose.macos.yml` (macOS compose file)

### Bluetooth Commands Configuration

The Bluetooth scanner supports predefined commands loaded from a configuration file:

**File Location**: `/media/{raspberry-pi-user}/HUBLINK/bluetooth_commands.json`

**File Format**:
```json
{
  "sendFiles": {
    "sendFiles": true
  },
  "timestamp": {
    "timestamp": -1
  },
  "getStatus": {
    "getStatus": true
  },
  "restartSensor": {
    "restart": "sensor"
  },
  "syncTime": {
    "timestamp": -1,
    "sendFilenames": true,
    "watchdogTimeoutMs": 10000
  }
}
```

**Template Variables**:
- `-1`: Special numeric placeholder replaced with current local Unix timestamp (integer)

**Format Features**:
- ✅ **Clean JSON objects** - No escaping needed, write native JSON
- ✅ **Template variables** - Use `-1` for timestamp placeholders
- ✅ **Nested structures** - Support for complex command objects
- ✅ **IDE friendly** - Full syntax highlighting and validation
- ✅ **Readable & maintainable** - Clear structure for complex commands

**Features**:
- **Automatic Detection**: File is loaded at application startup
- **Quick Commands**: Commands appear as buttons in a 4-column grid when connected to a device
- **Template Processing**: Variables like `-1` are automatically replaced with current timestamp
- **Responsive Design**: Grid adapts to 2 columns on tablets, 1 column on phones
- **Hover Tooltips**: Full command shown on button hover

### Logging

The application logs to both console and file:
- Log file: `hublink_hypervisor.log`
- Log level: DEBUG (during development)
- Format: Timestamp, logger name, level, and message

## Development Features

### Auto-Fix Capabilities

The hypervisor includes intelligent auto-fix functionality that automatically detects and resolves common issues:

- **BLE Error Resolution**: Automatically restarts Bluetooth services and containers when BLE errors are detected
- **Internet Connectivity Fixes**: Resolves network connectivity issues between hypervisor and containers
- **Generic Error Recovery**: Applies container restart sequences for various error conditions
- **Configurable Settings**: Auto-fix can be enabled/disabled via API or UI
- **Smart Timing**: Waits 5 minutes before applying fixes to avoid premature interventions
- **Environment Awareness**: Different fix strategies for development (macOS) vs production (Raspberry Pi) environments

### Caching System

- **Hublink Status Caching**: Prevents duplicate requests to Hublink `/status` endpoint with 5-second cache duration
- **Performance Optimization**: Reduces network load while maintaining real-time functionality

## Debugging

### Local Development
```bash
# Check logs in real-time
tail -f hublink_hypervisor.log

# View recent logs
cat hublink_hypervisor.log

# Check for errors
grep ERROR hublink_hypervisor.log
grep WARNING hublink_hypervisor.log
```

### Docker Deployment
```bash
# Check logs in real-time
docker logs -f hublink-hypervisor

# View recent logs
docker logs hublink-hypervisor
```

## Docker Development

### Building the Image

1. **Login to Docker Hub**:
   ```bash
   docker login
   ```

2. **Build and Push Image**:
   ```bash
   # For production (latest tag)
   docker buildx build --platform linux/arm64 \
     -t neurotechhub/hublink-hypervisor:latest \
     --push .

   # For development/testing (dev tag)
   docker buildx build --platform linux/arm64 \
     -t neurotechhub/hublink-hypervisor:dev \
     --push .
   ```

3. **Multi-platform Build** (optional):
   ```bash
   # Build for both ARM64 (Raspberry Pi) and AMD64 (development)
   docker buildx build --platform linux/arm64,linux/amd64 \
     -t neurotechhub/hublink-hypervisor:latest \
     --push .
   ```

### Local Docker Testing

```bash
# Build local image
docker build -t hublink-hypervisor:dev .

# Run with docker-compose
docker-compose up -d

# Check logs
docker logs -f hublink-hypervisor
```

## Error Handling

The application provides detailed error information:
- Container operation failures
- Internet connectivity issues
- Hublink API communication problems
- System-level errors
- Auto-fix intervention history and results

## Contributing

1. Follow the existing code style
2. Add comprehensive logging for new features
3. Test on both macOS and Raspberry Pi
4. Update documentation for new features
5. Ensure all API endpoints are properly documented

## License

This project is proprietary software for Hublink.cloud™.

---

**hublink.cloud™ Hypervisor** - Clean, minimal container management for Hublink systems. 