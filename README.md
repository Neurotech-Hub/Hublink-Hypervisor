# Hublink.cloud™ Hypervisor

A clean, minimal Flask web application for monitoring and controlling Hublink Docker containers on Raspberry Pi 5 or development machines.

## Features

- Real-time status monitoring of Hublink containers
- Start/Stop/Restart container controls
- Internet connectivity monitoring
- Container logs viewing
- Clean, minimal UI with responsive design
- Automatic updates via Watchtower
- Docker-based deployment for easy management

## Prerequisites

- Docker and Docker Compose
- Hublink containers running from `/opt/hublink` directory

## Installation

### Quick Installation (Recommended)

For installation on Raspberry Pi 5, download and run the setup script with a single command:

```bash
curl -sSL https://raw.githubusercontent.com/Neurotech-Hub/Hublink-Hypervisor/main/setup.sh | sudo bash
```

This will:
- Install the application as a Docker container
- Set up automatic updates via Watchtower
- Start the application on port 8081

The application will be available at `http://localhost:8081` and will start automatically on boot.

### Manual Docker Installation

1. **Pull the Docker image**:
   ```bash
   docker pull neurotechhub/hublink-hypervisor:latest
   ```

2. **Create a docker-compose file**:
   ```yaml
   version: '3.8'
   services:
     hublink-hypervisor:
       image: neurotechhub/hublink-hypervisor:latest
       container_name: hublink-hypervisor
       ports:
         - "8081:8081"
       volumes:
         - /var/run/docker.sock:/var/run/docker.sock:ro
         - /opt/hublink:/opt/hublink:ro
       environment:
         - HUBLINK_PATH=/opt/hublink
       restart: unless-stopped
       labels:
         - "com.centurylinklabs.watchtower.enable=true"
   ```

3. **Start the container**:
   ```bash
   docker-compose up -d
   ```

### Local Development Installation

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

#### Docker Deployment
```bash
# Start the container
docker-compose -f docker-compose.hypervisor.yml up -d

# Check status
docker ps | grep hublink-hypervisor

# View logs
docker logs -f hublink-hypervisor
```

#### Local Development
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
4. **Container Logs**: Real-time logs from the Hublink containers

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

### Container Logs
```bash
GET /api/logs
```
Get recent container logs.

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
├── app.py                           # Main Flask application
├── requirements.txt                 # Python dependencies
├── setup.sh                        # Docker installation script
├── start.sh                        # Development startup script
├── Dockerfile                      # Docker container definition
├── docker-compose.hypervisor.yml   # Docker Compose configuration
├── templates/
│   └── index.html                  # Main dashboard template
└── static/
    ├── css/
    │   └── style.css               # Custom CSS styles
    └── js/
        └── app.js                  # Frontend JavaScript
```

### Key Components

1. **HublinkManager**: Handles Docker container operations and status monitoring
2. **InternetChecker**: Checks internet connectivity for both app and containers
3. **Frontend**: Clean, responsive UI with real-time updates
4. **API**: RESTful endpoints for status and control operations

### Debugging

The application includes comprehensive logging:

#### Docker Deployment
```bash
# Check logs in real-time
docker logs -f hublink-hypervisor

# View recent logs
docker logs hublink-hypervisor
```

#### Local Development
```bash
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

## Container Management

### Container Commands

If installed via Docker, manage the Hublink Hypervisor container with:

```bash
# Check container status
docker ps | grep hublink-hypervisor

# Start the container
docker-compose -f /opt/hublink-hypervisor/docker-compose.hypervisor.yml up -d

# Stop the container
docker-compose -f /opt/hublink-hypervisor/docker-compose.hypervisor.yml down

# Restart the container
docker-compose -f /opt/hublink-hypervisor/docker-compose.hypervisor.yml restart

# View container logs
docker logs -f hublink-hypervisor

# View recent logs
docker logs --since "1h" hublink-hypervisor
```

### Auto-Updates

The container is configured for automatic updates via Watchtower. When a new version is pushed to Docker Hub, Watchtower will automatically:

1. Pull the latest image
2. Stop the current container
3. Start a new container with the updated image

### Manual Updates

To manually update the container:

```bash
# Pull latest image
docker pull neurotechhub/hublink-hypervisor:latest

# Restart container
docker-compose -f /opt/hublink-hypervisor/docker-compose.hypervisor.yml up -d
```

## Deployment

### Raspberry Pi 5

1. **Quick Installation** (Recommended):
   ```bash
   curl -sSL https://raw.githubusercontent.com/Neurotech-Hub/Hublink-Hypervisor/main/setup.sh | sudo bash
   ```

2. **Manual Docker Installation**:
   ```bash
   docker pull neurotechhub/hublink-hypervisor:latest
   # Create docker-compose.hypervisor.yml and run docker-compose up -d
   ```

### Development Machine (macOS)

1. **Docker Deployment**:
   ```bash
   docker pull neurotechhub/hublink-hypervisor:latest
   # Create docker-compose.hypervisor.yml and run docker-compose up -d
   ```

2. **Local Development**:
   ```bash
   brew install python3
   python3 -m venv venv
   source venv/bin/activate
   pip3 install -r requirements.txt
   python3 app.py
   ```

## Troubleshooting

### Common Issues

1. **Docker Socket Access**:
   - Ensure the container has access to `/var/run/docker.sock`
   - Check Docker socket permissions

2. **Permission Denied**:
   - Ensure the application has access to `/opt/hublink`
   - Check Docker permissions

3. **Container Not Found**:
   - Verify Hublink containers are in `/opt/hublink`
   - Check docker-compose file exists

4. **Internet Connectivity Issues**:
   - Check network configuration
   - Verify firewall settings

5. **Port Conflicts**:
   - Default port is 8081
   - Modify docker-compose file to change port if needed

### Log Analysis

#### Docker Deployment
```bash
# Check for errors
docker logs hublink-hypervisor | grep ERROR
docker logs hublink-hypervisor | grep WARNING
```

#### Local Development
```bash
# Check for errors
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