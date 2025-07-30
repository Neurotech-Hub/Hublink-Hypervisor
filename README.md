# Hublink.cloud™ Hypervisor

A clean, minimal Flask web application for monitoring and controlling Hublink Docker containers on Raspberry Pi 5 or development machines.

## Prerequisites

- Python 3.7+
- Docker and Docker Compose
- Hublink containers running from `/opt/hublink` directory

## Installation

### Quick Installation (Recommended)

For installation on Raspberry Pi 5, download and run the setup script with a single command:

```bash
curl -sSL https://raw.githubusercontent.com/Neurotech-Hub/Hublink-Hypervisor/main/setup.sh | sudo bash
```

This will:
- Install the application to `/opt/hublink-hypervisor`
- Create a Python virtual environment
- Install all dependencies
- Set up a systemd service for auto-start
- Configure logging
- Start the service automatically

The application will be available at `http://localhost:8081` and will start automatically on boot.

### Manual Installation

1. **Clone or download the application**:
   ```bash
   # If you have this as a repository
   git clone https://github.com/Neurotech-Hub/Hublink-Hypervisor.git
   cd Hublink-Hypervisor
   
   # Or if you have the files directly
   cd /path/to/Hublink-Hypervisor
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

## Usage

### Starting the Application

```bash
# Make sure your virtual environment is activated
source venv/bin/activate

# Start the application
python app.py
```

The application will start on `http://localhost:8081`

### Accessing the Dashboard

Open your web browser and navigate to:
```
http://localhost:8081
```

### Container Management

The dashboard provides three main container control actions:

- **Start**: Start all Hublink containers (only available when containers are stopped)
- **Stop**: Stop all Hublink containers (only available when containers are running)
- **Restart**: Restart all Hublink containers (only available when containers are running)

### Status Monitoring

The dashboard displays:

1. **Container Status**: Current state and details of Hublink containers
2. **Internet Connectivity**: Status of both hypervisor and Hublink container internet access
3. **System Health**: Overall system status with detailed error reporting
4. **Quick Actions**: Refresh status, view logs, and configuration options

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

### Internet Connectivity
```bash
GET /api/internet/check
```
Check internet connectivity for both hypervisor and Hublink container.

## Configuration

### Environment Variables

The application uses the following default configuration:

- `HUBLINK_PATH`: `/opt/hublink` (path to Hublink containers)
- `DOCKER_COMPOSE_FILE`: `docker-compose.yml` (standard compose file)
- `DOCKER_COMPOSE_MAC_FILE`: `docker-compose.macos.yml` (macOS compose file)

### Logging

The application logs to both console and file:
- Log file: `hublink_hypervisor.log`
- Log level: DEBUG (during development)
- Format: Timestamp, logger name, level, and message

## Development

### Project Structure
```
Hublink-Hypervisor/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── templates/
│   └── index.html        # Main dashboard template
└── static/
    ├── css/
    │   └── style.css     # Custom CSS styles
    └── js/
        └── app.js        # Frontend JavaScript
```

### Key Components

1. **HublinkManager**: Handles Docker container operations and status monitoring
2. **InternetChecker**: Checks internet connectivity for both app and containers
3. **Frontend**: Clean, responsive UI with real-time updates
4. **API**: RESTful endpoints for status and control operations

### Debugging

The application includes comprehensive logging:

```python
# Check logs in real-time
tail -f hublink_hypervisor.log

# View recent logs
cat hublink_hypervisor.log
```

### Error Handling

The application provides detailed error information:
- Container operation failures
- Internet connectivity issues
- Hublink API communication problems
- System-level errors

## Service Management

### Service Commands

If installed via the setup script, the Hublink Hypervisor runs as a systemd service:

```bash
# Check service status
sudo systemctl status hublink-hypervisor.service

# Start the service
sudo systemctl start hublink-hypervisor.service

# Stop the service
sudo systemctl stop hublink-hypervisor.service

# Restart the service
sudo systemctl restart hublink-hypervisor.service

# Enable auto-start on boot
sudo systemctl enable hublink-hypervisor.service

# Disable auto-start on boot
sudo systemctl disable hublink-hypervisor.service

# View service logs
sudo journalctl -u hublink-hypervisor.service -f

# View recent logs
sudo journalctl -u hublink-hypervisor.service --since "1 hour ago"
```

### Application Logs

Application logs are stored at:
```bash
/opt/hublink-hypervisor/logs/hublink-hypervisor.log
```

### Updating the Application

To update your installation with the latest files (overwrites local changes):

```bash
cd /opt/hublink-hypervisor
sudo git fetch origin
sudo git reset --hard origin/main
sudo systemctl restart hublink-hypervisor.service
```

This will:
- Fetch the latest changes from the repository
- Reset to the latest main branch (overwriting any local changes)
- Restart the service with the updated code

## Deployment

### Raspberry Pi 5

1. **Quick Installation** (Recommended):
   ```bash
   curl -sSL https://raw.githubusercontent.com/Neurotech-Hub/Hublink-Hypervisor/main/setup.sh | sudo bash
   ```

2. **Manual Installation**:
   ```bash
   sudo apt update
   sudo apt install python3 python3-pip
   pip3 install -r requirements.txt
   ```

### Development Machine (macOS)

1. **Install dependencies**:
   ```bash
   brew install python3
   pip3 install -r requirements.txt
   ```

2. **Create and activate virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip3 install -r requirements.txt
   ```

3. **Run in development mode**:
   ```bash
   source venv/bin/activate
   python3 app.py
   ```

## Troubleshooting

### Common Issues

1. **Permission Denied**:
   - Ensure the application has access to `/opt/hublink`
   - Check Docker permissions

2. **Container Not Found**:
   - Verify Hublink containers are in `/opt/hublink`
   - Check docker-compose file exists

3. **Internet Connectivity Issues**:
   - Check network configuration
   - Verify firewall settings

4. **Port Conflicts**:
   - Default port is 8081
   - Modify `app.py` to change port if needed

### Log Analysis

Check the log file for detailed error information:
```bash
grep ERROR hublink_hypervisor.log
grep WARNING hublink_hypervisor.log
```

## Contributing

1. Follow the existing code style
2. Add comprehensive logging for new features
3. Test on both macOS and Raspberry Pi
4. Update documentation for new features

## License

This project is proprietary software for Hublink.cloud™.

---

**hublink.cloud™ Hypervisor** - Clean, minimal container management for Hublink systems. 