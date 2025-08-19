#!/usr/bin/env python3
"""
Hublink Hypervisor - Flask Application
Provides status monitoring and control for Hublink Docker containers
"""

import os
import json
import subprocess
import requests
import time
import platform
from datetime import datetime
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import logging
import docker

# Import scanner module
try:
    from modules.scanner import scanner_bp
    SCANNER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Scanner module not available: {e}")
    SCANNER_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Changed from DEBUG to INFO
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('hublink_hypervisor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Reduce verbosity of specific loggers
logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)
logging.getLogger('werkzeug').setLevel(logging.WARNING)
logging.getLogger('docker').setLevel(logging.WARNING)

app = Flask(__name__)
CORS(app)  # Enable CORS for development

# Register scanner blueprint if available
if SCANNER_AVAILABLE:
    app.register_blueprint(scanner_bp)
    logger.info("Scanner module registered successfully")
else:
    logger.warning("Scanner module not available - scanner functionality disabled")

# Scanner page route
@app.route('/scanner')
def scanner_page():
    """Standalone scanner page"""
    return render_template('scanner.html')

# Configuration
HUBLINK_PATH = '/opt/hublink'
DOCKER_COMPOSE_FILE = 'docker-compose.yml'
DOCKER_COMPOSE_MAC_FILE = 'docker-compose.macos.yml'

def detect_environment():
    """Detect if we're running in development (macOS) or production (Linux) environment"""
    try:
        # Method 1: Check if we're inside a Docker container and get host info
        if os.path.exists('/.dockerenv'):
            logger.info("Running inside Docker container, checking host system...")
            try:
                # Use Docker API to get host system information
                import docker
                client = docker.from_env()
                info = client.info()
                
                if 'OperatingSystem' in info:
                    os_name = info['OperatingSystem']
                    logger.info(f"Docker host OS: {os_name}")
                    
                    if 'macOS' in os_name or 'Darwin' in os_name:
                        logger.info("Environment detected: Docker Desktop on macOS (Development)")
                        return "development"
                    elif 'Linux' in os_name:
                        # Check if it's a Raspberry Pi
                        if 'Raspberry Pi' in os_name or 'arm' in os_name.lower():
                            logger.info("Environment detected: Docker on Raspberry Pi (Production)")
                            return "production"
                        else:
                            logger.info("Environment detected: Docker on Linux (Production)")
                            return "production"
                
                # Fallback: Check Docker Desktop specific indicators
                if 'Docker Desktop' in str(info):
                    logger.info("Environment detected: Docker Desktop detected (Development)")
                    return "development"
                    
            except Exception as e:
                logger.warning(f"Could not get Docker host info: {e}")
        
        # Method 2: Check the container's system (fallback)
        import subprocess
        result = subprocess.run(['uname', '-s'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            system = result.stdout.strip()
            if system == "Darwin":  # macOS (if running natively)
                logger.info("Environment detected: macOS (Development)")
                return "development"
            elif system == "Linux":  # Linux
                # Check for Raspberry Pi specific indicators
                try:
                    if os.path.exists('/proc/cpuinfo'):
                        with open('/proc/cpuinfo', 'r') as f:
                            cpuinfo = f.read()
                            if 'Raspberry Pi' in cpuinfo or 'BCM2708' in cpuinfo or 'BCM2835' in cpuinfo:
                                logger.info("Environment detected: Raspberry Pi (Production)")
                                return "production"
                    
                    # Check for ARM architecture
                    arch_result = subprocess.run(['uname', '-m'], capture_output=True, text=True, timeout=5)
                    if arch_result.returncode == 0:
                        arch = arch_result.stdout.strip()
                        if arch in ['armv7l', 'aarch64', 'arm64']:
                            logger.info("Environment detected: ARM Linux (Production)")
                            return "production"
                except Exception:
                    pass
        
        # Method 3: Check Python platform (least reliable in container)
        import platform
        system = platform.system()
        if system == "Darwin":
            logger.info("Environment detected: macOS via Python platform (Development)")
            return "development"
        elif system == "Linux":
            logger.info("Environment detected: Linux via Python platform (Production)")
            return "production"
        
        # Ultimate fallback - assume production if we can't determine
        logger.warning("Could not detect environment, defaulting to production")
        return "production"
        
    except Exception as e:
        logger.error(f"Error detecting environment: {e}")
        logger.warning("Could not detect environment, defaulting to production")
        return "production"

# Detect environment at startup
ENVIRONMENT = detect_environment()
IS_DEVELOPMENT = ENVIRONMENT == "development"
IS_PRODUCTION = ENVIRONMENT == "production"

logger.info(f"Environment: {ENVIRONMENT} (Development: {IS_DEVELOPMENT}, Production: {IS_PRODUCTION})")

def get_hublink_port():
    """Dynamically determine the correct port for Hublink container"""
    # Use environment detection to determine default port
    if IS_DEVELOPMENT:
        default_port = 6000
        logger.info("Development environment detected, using port 6000")
    else:
        default_port = 5000
        logger.info("Production environment detected, using port 5000")
    
    # Try the default port first, then the other port as fallback
    for attempt in range(3):
        for port in [default_port, 5000 if default_port == 6000 else 6000]:
            # Try multiple host addresses
            for host in ['localhost', '127.0.0.1', 'host.docker.internal']:
                try:
                    logger.info(f"Startup: Testing Hublink connection to {host}:{port}/status")
                    response = requests.get(f"http://{host}:{port}/status", timeout=3)
                    if response.status_code in [200, 500]:  # Accept both 200 and 500 as valid responses
                        logger.info(f"Hublink container found on {host}:{port}")
                        return port
                except requests.exceptions.RequestException:
                    continue
        
        if attempt < 2:  # Don't sleep on the last attempt
            logger.debug(f"Port detection attempt {attempt + 1} failed, retrying in 2 seconds...")
            time.sleep(2)
    
    # Return the default port for the environment
    logger.info(f"No container found, using default port {default_port} for {ENVIRONMENT} environment")
    return default_port

HUBLINK_PORT = get_hublink_port()
logger.info(f"Using Hublink port: {HUBLINK_PORT}")

def get_hublink_host():
    """Get the correct host for Hublink container communication"""
    # Try multiple host addresses to find the one that works
    for host in ['localhost', '127.0.0.1', 'host.docker.internal']:
        try:
            logger.info(f"Startup: Testing Hublink host {host}:{HUBLINK_PORT}/status")
            response = requests.get(f"http://{host}:{HUBLINK_PORT}/status", timeout=2)
            if response.status_code in [200, 500]:
                logger.debug(f"Using host {host} for Hublink communication")
                return host
        except requests.exceptions.RequestException:
            continue
    
    # Default to localhost if none work
    logger.warning("Could not detect working host, defaulting to localhost")
    return 'localhost'

HUBLINK_HOST = get_hublink_host()

# Global auto-fix state
auto_fix_enabled = True  # Enable auto-fix by default
issue_start_time = None
last_fix_attempt = None

# Debug: Track requests to Hublink /status endpoint
hublink_status_request_count = 0

# Cache for Hublink status to prevent duplicate requests
hublink_status_cache = {
    'data': None,
    'timestamp': 0,
    'cache_duration': 5  # Cache for 5 seconds
}

def get_cached_hublink_status():
    """Get Hublink status from cache or make a new request if cache is expired"""
    global hublink_status_cache
    
    current_time = time.time()
    
    # Check if cache is still valid
    if (hublink_status_cache['data'] is not None and 
        current_time - hublink_status_cache['timestamp'] < hublink_status_cache['cache_duration']):
        logger.debug("Using cached Hublink status")
        return hublink_status_cache['data']
    
    # Cache is expired or empty, make a new request
    try:
        global hublink_status_request_count
        hublink_status_request_count += 1
        logger.info(f"Making request #{hublink_status_request_count} to Hublink /status endpoint")
        
        response = requests.get(f"http://{HUBLINK_HOST}:{HUBLINK_PORT}/status", timeout=3)
        if response.status_code in [200, 500]:  # Accept both 200 and 500 as valid responses
            hublink_status = response.json()
            logger.debug(f"Hublink API connected via {HUBLINK_HOST}:{HUBLINK_PORT}")
            
            # Cache the result
            hublink_status_cache['data'] = hublink_status
            hublink_status_cache['timestamp'] = current_time
            
            return hublink_status
        else:
            logger.debug(f"Hublink container status check failed with status: {response.status_code}")
            return None
    except Exception as e:
        logger.debug(f"Hublink container status check failed - connection refused: {e}")
        return None

class AutoFixManager:
    """Manages automatic fixing of container issues"""
    
    def __init__(self):
        self.hublink_manager = None  # Will be set after HublinkManager initialization
    
    def set_hublink_manager(self, hublink_manager):
        """Set reference to HublinkManager for container operations"""
        self.hublink_manager = hublink_manager
    
    def check_and_fix_issues(self, container_state, container_errors, app_internet, hublink_internet):
        """Check if auto-fix is needed and apply fixes"""
        global auto_fix_enabled, issue_start_time, last_fix_attempt
        
        if not auto_fix_enabled:
            return False
        
        # Don't auto-fix if container is intentionally stopped
        if container_state and container_state.get('state') == 'stopped':
            logger.debug("Container is intentionally stopped - not auto-fixing")
            issue_start_time = None
            return False
        
        # Check if container is unhealthy OR has application-level errors
        is_unhealthy = False
        has_application_errors = container_errors and len(container_errors) > 0
        
        if container_state and container_state.get('state') == 'running':
            containers = container_state.get('containers', [])
            if containers:
                container = containers[0]
                if 'unhealthy' in container.get('status', '').lower():
                    is_unhealthy = True
        
        # Only proceed if container is unhealthy OR has application errors
        if not is_unhealthy and not has_application_errors:
            # Container is healthy and no application errors, reset timer
            issue_start_time = None
            return False
        
        # Container is unhealthy or has application errors, start or check timer
        current_time = time.time()
        if issue_start_time is None:
            issue_start_time = current_time
            if is_unhealthy:
                logger.info("Container became unhealthy, starting auto-fix timer")
            else:
                logger.info("Application errors detected, starting auto-fix timer")
            return False
        
        # Check if issues persist for more than 5 minutes
        issue_duration = current_time - issue_start_time
        if issue_duration < 300:  # Less than 5 minutes
            if is_unhealthy:
                logger.debug(f"Container unhealthy for {issue_duration:.1f}s, waiting for 300s threshold")
            else:
                logger.debug(f"Application errors present for {issue_duration:.1f}s, waiting for 300s threshold")
            return False
        
        # Check if we've already attempted a fix recently (prevent spam)
        if last_fix_attempt and (current_time - last_fix_attempt) < 300:  # 5 minutes
            logger.debug("Fix attempted recently, waiting before next attempt")
            return False
        
        # Check for BLE errors
        if self._has_ble_error(container_errors):
            logger.info("BLE error detected, applying BLE fix sequence")
            last_fix_attempt = current_time
            return self._apply_ble_fix()
        
        # Check for internet connectivity issue: hypervisor has internet but container doesn't
        if app_internet and not hublink_internet and container_state.get('state') == 'running':
            logger.info("Internet connectivity issue detected: hypervisor connected but container disconnected")
            last_fix_attempt = current_time
            return self._apply_internet_fix()
        
        # Check for any other errors (generic fix)
        if container_errors and len(container_errors) > 0:
            logger.info(f"Generic error detected: {list(container_errors.keys())}, applying generic fix")
            last_fix_attempt = current_time
            return self._apply_generic_fix()
        
        return False
    
    def _has_ble_error(self, container_errors):
        """Check if the error contains BLE-related issues"""
        if not container_errors:
            return False
        
        # Check all error messages for BLE keywords
        for category, error in container_errors.items():
            if isinstance(error, str) and 'ble' in error.lower():
                return True
        return False
    
    def _apply_ble_fix(self):
        """Apply BLE fix sequence"""
        try:
            logger.info("Starting BLE fix sequence")
            
            if IS_DEVELOPMENT:
                logger.info("Development environment detected, skipping system-level BLE commands")
                logger.info("Only restarting container for BLE fix test")
                
                # Step 1: Stop the hublink container
                logger.info("Step 1: Stopping hublink container")
                if self.hublink_manager:
                    result = self.hublink_manager.stop_containers()
                    if not result.get('success'):
                        logger.error("Failed to stop hublink container")
                        return False
                
                # Wait for container to fully stop
                logger.info("Waiting for container to fully stop...")
                time.sleep(10)
                
                # Step 2: Start the hublink container (development mode - just restart)
                logger.info("Step 2: Starting hublink container (development mode)")
                if self.hublink_manager:
                    result = self.hublink_manager.start_containers()
                    if not result.get('success'):
                        logger.error("Failed to start hublink container")
                        return False
                
                logger.info("BLE fix sequence completed (development mode)")
                return True
            
            else:
                logger.info("Production environment detected, applying full BLE fix sequence")
                
                # Step 1: Stop the hublink container
                logger.info("Step 1: Stopping hublink container")
                if self.hublink_manager:
                    result = self.hublink_manager.stop_containers()
                    if not result.get('success'):
                        logger.error("Failed to stop hublink container")
                        return False
                
                # Wait for container to fully stop
                logger.info("Waiting for container to fully stop...")
                time.sleep(10)
                
                # Step 2: Stop bluetooth service on host via Docker
                logger.info("Step 2: Stopping bluetooth service on host")
                try:
                    result = subprocess.run([
                        'docker', 'run', '--rm', '--privileged', '--network=host',
                        '--pid=host', '--volume=/sys:/sys', '--volume=/dev:/dev',
                        'alpine:latest', 'sh', '-c',
                        'apk add --no-cache systemctl && systemctl stop bluetooth'
                    ], capture_output=True, text=True, timeout=30)
                    
                    if result.returncode == 0:
                        logger.info("Successfully stopped bluetooth service")
                    else:
                        logger.warning(f"Failed to stop bluetooth service: {result.stderr}")
                        
                except Exception as e:
                    logger.warning(f"Could not stop bluetooth service: {e}")
                
                # Step 3: Kill bluetoothd process on host
                logger.info("Step 3: Killing bluetoothd process on host")
                try:
                    result = subprocess.run([
                        'docker', 'run', '--rm', '--privileged', '--network=host',
                        '--pid=host', 'alpine:latest', 'sh', '-c',
                        'pkill -9 bluetoothd || true'
                    ], capture_output=True, text=True, timeout=30)
                    
                    if result.returncode in [0, 1]:  # pkill returns 1 if no processes found
                        logger.info("Successfully killed bluetoothd processes")
                    else:
                        logger.warning(f"Unexpected pkill result: {result.stderr}")
                        
                except Exception as e:
                    logger.warning(f"Could not kill bluetoothd processes: {e}")
                
                # Step 4: Remove btusb module on host
                logger.info("Step 4: Removing btusb module on host")
                try:
                    result = subprocess.run([
                        'docker', 'run', '--rm', '--privileged', '--network=host',
                        '--volume=/sys:/sys', 'alpine:latest', 'sh', '-c',
                        'apk add --no-cache kmod && modprobe -r btusb'
                    ], capture_output=True, text=True, timeout=30)
                    
                    if result.returncode == 0:
                        logger.info("Successfully removed btusb module")
                    else:
                        logger.warning(f"Failed to remove btusb module: {result.stderr}")
                        
                except Exception as e:
                    logger.warning(f"Could not remove btusb module: {e}")
                
                # Step 5: Reload btusb module on host
                logger.info("Step 5: Reloading btusb module on host")
                try:
                    result = subprocess.run([
                        'docker', 'run', '--rm', '--privileged', '--network=host',
                        '--volume=/sys:/sys', 'alpine:latest', 'sh', '-c',
                        'apk add --no-cache kmod && modprobe btusb'
                    ], capture_output=True, text=True, timeout=30)
                    
                    if result.returncode == 0:
                        logger.info("Successfully reloaded btusb module")
                    else:
                        logger.warning(f"Failed to reload btusb module: {result.stderr}")
                        
                except Exception as e:
                    logger.warning(f"Could not reload btusb module: {e}")
                
                # Step 6: Start bluetooth service on host
                logger.info("Step 6: Starting bluetooth service on host")
                try:
                    result = subprocess.run([
                        'docker', 'run', '--rm', '--privileged', '--network=host',
                        '--pid=host', '--volume=/sys:/sys', '--volume=/dev:/dev',
                        'alpine:latest', 'sh', '-c',
                        'apk add --no-cache systemctl && systemctl start bluetooth'
                    ], capture_output=True, text=True, timeout=30)
                    
                    if result.returncode == 0:
                        logger.info("Successfully started bluetooth service")
                    else:
                        logger.warning(f"Failed to start bluetooth service: {result.stderr}")
                        
                except Exception as e:
                    logger.warning(f"Could not start bluetooth service: {e}")
                
                # Wait for bluetooth to initialize
                logger.info("Waiting for bluetooth to initialize...")
                time.sleep(5)
                
                # Step 7: Start the hublink container
                logger.info("Step 7: Starting hublink container")
                if self.hublink_manager:
                    result = self.hublink_manager.start_containers()
                    if not result.get('success'):
                        logger.error("Failed to start hublink container")
                        return False
                
                logger.info("BLE fix sequence completed successfully")
                return True
            
        except Exception as e:
            logger.error(f"Error during BLE fix sequence: {e}")
            return False

    def _apply_internet_fix(self):
        """Apply internet connectivity fix: docker down then up"""
        try:
            logger.info("Starting internet connectivity fix sequence")
            
            # Step 1: Stop the hublink container
            logger.info("Step 1: Stopping hublink container")
            if self.hublink_manager:
                result = self.hublink_manager.stop_containers()
                if not result.get('success'):
                    logger.error("Failed to stop hublink container")
                    return False
            
            # Wait for container to fully stop
            logger.info("Waiting for container to fully stop...")
            time.sleep(10)
            
            # Step 2: Start the hublink container
            logger.info("Step 2: Starting hublink container")
            if self.hublink_manager:
                result = self.hublink_manager.start_containers()
                if not result.get('success'):
                    logger.error("Failed to start hublink container")
                    return False
            
            logger.info("Internet connectivity fix sequence completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error during internet connectivity fix sequence: {e}")
            return False

    def _apply_generic_fix(self):
        """Apply generic fix for any error: docker down then up"""
        try:
            logger.info("Starting generic fix sequence")
            
            # Step 1: Stop the hublink container
            logger.info("Step 1: Stopping hublink container")
            if self.hublink_manager:
                result = self.hublink_manager.stop_containers()
                if not result.get('success'):
                    logger.error("Failed to stop hublink container")
                    return False
            
            # Wait for container to fully stop
            logger.info("Waiting for container to fully stop...")
            time.sleep(10)
            
            # Step 2: Start the hublink container
            logger.info("Step 2: Starting hublink container")
            if self.hublink_manager:
                result = self.hublink_manager.start_containers()
                if not result.get('success'):
                    logger.error("Failed to start hublink container")
                    return False
            
            logger.info("Generic fix sequence completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error during generic fix sequence: {e}")
            return False

class HublinkManager:
    """Manages Hublink Docker container operations and status monitoring"""
    
    def __init__(self):
        self.hublink_path = HUBLINK_PATH
        self.compose_file = self._get_compose_file()
        try:
            self.docker_client = docker.from_env()
            logger.info("Successfully initialized Docker client")
        except Exception as e:
            logger.warning(f"Failed to initialize Docker client: {e}")
            self.docker_client = None
        logger.info(f"Initialized HublinkManager with path: {self.hublink_path}")
        logger.info(f"Using compose file: {self.compose_file}")
    
    def _get_compose_file(self):
        """Determine which docker-compose file to use based on environment detection"""
        if IS_DEVELOPMENT:
            # Development environment - try macOS compose file first
            if os.path.exists(os.path.join(self.hublink_path, DOCKER_COMPOSE_MAC_FILE)):
                logger.info(f"Development environment detected, using {DOCKER_COMPOSE_MAC_FILE}")
                return DOCKER_COMPOSE_MAC_FILE
            else:
                logger.warning(f"Development environment detected but {DOCKER_COMPOSE_MAC_FILE} not found, falling back to {DOCKER_COMPOSE_FILE}")
                return DOCKER_COMPOSE_FILE
        else:
            # Production environment - use standard compose file
            if os.path.exists(os.path.join(self.hublink_path, DOCKER_COMPOSE_FILE)):
                logger.info(f"Production environment detected, using {DOCKER_COMPOSE_FILE}")
                return DOCKER_COMPOSE_FILE
            else:
                logger.error(f"No {DOCKER_COMPOSE_FILE} found in {self.hublink_path}")
                return DOCKER_COMPOSE_FILE
    
    def _run_docker_command(self, command, timeout=30):
        """Execute docker-compose command with error handling"""
        try:
            logger.debug(f"Executing docker command: {command}")
            result = subprocess.run(
                command,
                shell=True,
                cwd=self.hublink_path,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            logger.debug(f"Command output: {result.stdout}")
            if result.stderr:
                logger.warning(f"Command stderr: {result.stderr}")
            return result
        except subprocess.TimeoutExpired:
            logger.error(f"Docker command timed out: {command}")
            return None
        except Exception as e:
            logger.error(f"Error executing docker command: {e}")
            return None
    
    def get_container_status(self):
        """Get detailed status of Hublink containers"""
        try:
            
            # Try using Docker Python SDK first
            if self.docker_client:
                try:
                    containers = []
                    for container in self.docker_client.containers.list(all=True):
                        # Get detailed status from container attributes
                        detailed_status = container.attrs.get('State', {}).get('Status', container.status)
                        
                        # Get uptime information
                        started_at = container.attrs.get('State', {}).get('StartedAt')
                        uptime_info = ""
                        if started_at and started_at != "0001-01-01T00:00:00Z":
                            try:
                                # Parse the started time and calculate uptime
                                from datetime import datetime
                                start_time = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
                                current_time = datetime.now(start_time.tzinfo)
                                uptime_delta = current_time - start_time
                                
                                # Format uptime
                                if uptime_delta.days > 0:
                                    uptime_info = f"Up {uptime_delta.days} day{'s' if uptime_delta.days != 1 else ''}"
                                elif uptime_delta.seconds >= 3600:
                                    hours = uptime_delta.seconds // 3600
                                    uptime_info = f"Up {hours} hour{'s' if hours != 1 else ''}"
                                elif uptime_delta.seconds >= 60:
                                    minutes = uptime_delta.seconds // 60
                                    uptime_info = f"Up {minutes} minute{'s' if minutes != 1 else ''}"
                                else:
                                    uptime_info = "Up just now"
                            except Exception as e:
                                logger.debug(f"Error calculating uptime: {e}")
                                uptime_info = "Up"
                        
                        # Get health status
                        health_status = container.attrs.get('State', {}).get('Health', {}).get('Status', '')
                        if health_status:
                            detailed_status = f"{uptime_info} ({health_status})" if uptime_info else f"Up ({health_status})"
                        else:
                            detailed_status = uptime_info if uptime_info else "Up"
                        
                        # Get ports
                        ports = []
                        if container.attrs.get('NetworkSettings', {}).get('Ports'):
                            for port_mapping in container.attrs['NetworkSettings']['Ports'].values():
                                if port_mapping:
                                    ports.extend([p['HostPort'] for p in port_mapping])
                        ports_str = ', '.join(ports) if ports else ''
                        
                        containers.append({
                            "name": container.name,
                            "status": detailed_status,
                            "ports": ports_str,
                            "image": container.image.tags[0] if container.image.tags else container.image.id
                        })
                    
                    # Check for active Hublink gateway containers (exclude hypervisor and watchtower)
                    hublink_containers = [
                        c for c in containers 
                        if 'hublink-gateway' in c['name'].lower() 
                        and 'hypervisor' not in c['name'].lower()
                        and 'watchtower' not in c['name'].lower()
                        and c['status'] != 'exited'
                        and 'Exited' not in c['status']
                        and 'Created' not in c['status']
                    ]
                    
                    logger.debug(f"Found {len(hublink_containers)} Hublink containers using Docker SDK")
                    return {
                        "containers": hublink_containers,  # Only return filtered containers for display
                        "hublink_containers": hublink_containers,
                        "timestamp": time.time()
                    }
                except Exception as e:
                    logger.debug(f"Docker SDK failed, falling back to shell commands: {e}")
            
            # Fallback to shell commands
            logger.debug("Using shell commands to get container status")
            result = self._run_docker_command("docker ps -a --format '{{.Names}}|{{.Status}}|{{.Ports}}|{{.Image}}'")
            if not result or result.returncode != 0:
                logger.error("Failed to get container status")
                return {"error": "Failed to get container status"}
            
            containers = []
            lines = result.stdout.strip().split('\n')
            
            for line in lines:
                if line.strip():
                    parts = line.split('|')
                    if len(parts) >= 4:
                        containers.append({
                            "name": parts[0].strip(),
                            "status": parts[1].strip(),
                            "ports": parts[2].strip(),
                            "image": parts[3].strip()
                        })
            
            # Check for active Hublink gateway containers (exclude hypervisor and watchtower)
            hublink_containers = [
                c for c in containers 
                if 'hublink-gateway' in c['name'].lower() 
                and 'hypervisor' not in c['name'].lower()
                and 'watchtower' not in c['name'].lower()
                and c['status'] != 'exited'
                and 'Exited' not in c['status']
                and 'Created' not in c['status']
            ]
            
            logger.debug(f"Found {len(hublink_containers)} Hublink containers using shell commands")
            return {
                "containers": hublink_containers,  # Only return filtered containers for display
                "hublink_containers": hublink_containers,
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"Error getting container status: {e}")
            return {"error": str(e)}
    
    def get_container_state(self, force_refresh=False):
        """Get simplified container state for UI"""
        try:
            # Clear cache if force_refresh is requested
            if force_refresh:
                logger.debug("Force refreshing container state")
                # Clear any cached container info
                if hasattr(self, 'docker_client') and self.docker_client:
                    try:
                        self.docker_client.containers.list()  # Force refresh
                    except Exception:
                        pass
            
            status = self.get_container_status()
            if "error" in status:
                return status
            
            hublink_containers = status.get("hublink_containers", [])
            
            if not hublink_containers:
                return {
                    "state": "not_found",
                    "message": "No Hublink containers found",
                    "can_start": True,
                    "can_stop": False,
                    "can_restart": False
                }
            
            # Check if any container is running (handle both SDK and shell command formats)
            running_containers = [c for c in hublink_containers if c["status"] == "running" or "Up" in c["status"]]
            
            if running_containers:
                return {
                    "state": "running",
                    "message": f"{len(running_containers)} container(s) running",
                    "containers": running_containers,
                    "can_start": False,
                    "can_stop": True,
                    "can_restart": True
                }
            else:
                return {
                    "state": "stopped",
                    "message": "All containers stopped",
                    "containers": hublink_containers,
                    "can_start": True,
                    "can_stop": False,
                    "can_restart": False
                }
                
        except Exception as e:
            logger.error(f"Error getting container state: {e}")
            return {"error": str(e)}
    
    def start_containers(self):
        """Start Hublink containers"""
        try:
            logger.info("Starting Hublink containers")
            result = self._run_docker_command(f"docker compose -f {self.compose_file} up -d", timeout=60)
            
            if result and result.returncode == 0:
                logger.info("Successfully started Hublink containers")
                return {"success": True, "message": "Containers started successfully"}
            else:
                error_msg = result.stderr if result else "Unknown error"
                logger.error(f"Failed to start containers: {error_msg}")
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            logger.error(f"Error starting containers: {e}")
            return {"success": False, "error": str(e)}
    
    def stop_containers(self):
        """Stop Hublink containers"""
        try:
            logger.info("Stopping Hublink containers")
            result = self._run_docker_command(f"docker compose -f {self.compose_file} down", timeout=45)
            
            if result and result.returncode == 0:
                logger.info("Successfully stopped Hublink containers")
                return {"success": True, "message": "Containers stopped successfully"}
            else:
                error_msg = result.stderr if result else "Unknown error"
                logger.error(f"Failed to stop containers: {error_msg}")
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            logger.error(f"Error stopping containers: {e}")
            return {"success": False, "error": str(e)}
    
    def restart_containers(self):
        """Restart Hublink containers"""
        try:
            logger.info("Restarting Hublink containers")
            # Stop first
            stop_result = self.stop_containers()
            if not stop_result.get("success"):
                return stop_result
            
            # Wait for containers to fully stop
            time.sleep(3)
            
            # Start again
            start_result = self.start_containers()
            if start_result.get("success"):
                logger.info("Successfully restarted Hublink containers")
                return {"success": True, "message": "Containers restarted successfully"}
            else:
                return start_result
                
        except Exception as e:
            logger.error(f"Error restarting containers: {e}")
            return {"success": False, "error": str(e)}

class InternetChecker:
    """Checks internet connectivity for both the app and Hublink container"""
    
    @staticmethod
    def check_app_internet():
        """Check if the hypervisor app has internet connectivity"""
        try:
            # Try multiple reliable endpoints
            endpoints = [
                "https://www.google.com",
                "https://www.cloudflare.com",
                "https://httpbin.org/get"
            ]
            
            for endpoint in endpoints:
                try:
                    response = requests.get(endpoint, timeout=3)
                    if response.status_code in [200, 301, 302]:
                        return True
                except Exception as e:
                    continue
            
            logger.warning("App internet check failed for all endpoints")
            return False
        except Exception as e:
            logger.error(f"App internet check failed: {e}")
            return False

# Initialize managers
hublink_manager = HublinkManager()
internet_checker = InternetChecker()
auto_fix_manager = AutoFixManager()
auto_fix_manager.set_hublink_manager(hublink_manager)

@app.route('/')
def index():
    """Main dashboard page"""
    logger.debug("Serving main dashboard")
    return render_template('index.html')



@app.route('/api/status')
def status():
    """Get comprehensive system status"""
    try:
        # Check internet connectivity first
        app_internet = internet_checker.check_app_internet()
        
        # Get container state with improved detection
        container_state = hublink_manager.get_container_state()
        
        # Initialize error tracking
        errors = {}
        timestamps = {}
        
        # Check Hublink API status and correlate with container state
        hublink_status = None
        secret_url = None
        gateway_name = None
        hublink_internet = False
        
        # If container state shows running, verify it's actually accessible
        if container_state.get("state") == "running":
            try:
                # Use cached Hublink status to prevent duplicate requests
                hublink_status = get_cached_hublink_status()
                if hublink_status:
                    logger.debug(f"Hublink API connected via {HUBLINK_HOST}:{HUBLINK_PORT}")
                    # Get all the information we need from this single call
                    hublink_internet = hublink_status.get("internet_connected", False)
                    secret_url = hublink_status.get("secret_url")
                    gateway_name = hublink_status.get("gateway_name")
                    # Merge any Hublink errors
                    if hublink_status.get("status") == "error":
                        errors.update(hublink_status.get("errors", {}))
                        timestamps.update(hublink_status.get("timestamps", {}))
                else:
                    # API connection failed - this likely means container is actually down
                    # despite what container_state says. Let's re-check container state.
                    logger.warning("Hublink API connection failed, re-checking container state")
                    container_state = hublink_manager.get_container_state(force_refresh=True)
                    
                    if container_state.get("state") != "running":
                        logger.info("Container state corrected: container is actually stopped")
                    else:
                        # Container shows running but API is unreachable - this is a real error
                        errors["hublink_api"] = f"Container appears running but API is unreachable"
                        timestamps["hublink_api"] = time.time()
            except Exception as e:
                # API connection failed - re-check container state
                logger.warning(f"Hublink API connection failed: {e}, re-checking container state")
                container_state = hublink_manager.get_container_state(force_refresh=True)
                
                if container_state.get("state") != "running":
                    logger.info("Container state corrected: container is actually stopped")
                else:
                    errors["hublink_api"] = f"Failed to connect to Hublink API: {str(e)}"
                    timestamps["hublink_api"] = time.time()
        
        # Determine overall status
        
        if "error" in container_state:
            errors["container"] = container_state["error"]
            timestamps["container"] = time.time()
        
        if not app_internet:
            errors["app_internet"] = "Hypervisor app has no internet connectivity"
            timestamps["app_internet"] = time.time()
        
        # Only add hublink_internet error if we can't connect to the container at all
        # The container's own status endpoint will report its specific issues
        if container_state.get("state") == "running" and not hublink_internet:
            errors["hublink_internet"] = "Hublink container has no internet connectivity"
            timestamps["hublink_internet"] = time.time()
        
        # Check for auto-fix opportunities (only if container is supposed to be running)
        auto_fix_applied = False
        if container_state.get("state") in ["running", "not_found"]:
            # Only auto-fix if container should be running but has issues
            auto_fix_applied = auto_fix_manager.check_and_fix_issues(container_state, errors, app_internet, hublink_internet)
        else:
            logger.debug("Container is stopped - skipping auto-fix (user may have intentionally stopped it)")
        
        # Get scanner status if available
        scanner_status = None
        if SCANNER_AVAILABLE:
            try:
                from modules.scanner.scanner import scanner_instance
                scanner_status = scanner_instance.get_status()
            except Exception as e:
                logger.debug(f"Could not get scanner status: {e}")
        
        # Determine overall status
        if errors:
            status_response = {
                "status": "error",
                "errors": errors,
                "timestamps": timestamps,
                "internet_connected": app_internet,
                "hublink_internet_connected": hublink_internet,
                "container_state": container_state,
                "hublink_status": hublink_status,
                "secret_url": secret_url,
                "gateway_name": gateway_name,
                "auto_fix_applied": auto_fix_applied,
                "scanner_status": scanner_status,
                "timestamp": time.time()
            }
        else:
            status_response = {
                "status": "healthy",
                "internet_connected": app_internet,
                "hublink_internet_connected": hublink_internet,
                "container_state": container_state,
                "hublink_status": hublink_status,
                "secret_url": secret_url,
                "gateway_name": gateway_name,
                "auto_fix_applied": auto_fix_applied,
                "scanner_status": scanner_status,
                "timestamp": time.time()
            }
        
        return jsonify(status_response)
        
    except Exception as e:
        logger.error(f"Error in status endpoint: {e}")
        return jsonify({
            "status": "error",
            "errors": {"general": str(e)},
            "timestamps": {"general": time.time()},
            "timestamp": time.time()
        }), 500

@app.route('/api/containers')
def containers():
    """Get detailed container information"""
    logger.debug("Container details requested")
    return jsonify(hublink_manager.get_container_status())

@app.route('/api/containers/state')
def container_state():
    """Get simplified container state for UI"""
    logger.debug("Container state requested")
    return jsonify(hublink_manager.get_container_state())

@app.route('/api/containers/start', methods=['POST'])
def start_containers():
    """Start Hublink containers"""
    logger.info("Start containers requested")
    result = hublink_manager.start_containers()
    if result.get("success"):
        return jsonify(result), 200
    else:
        return jsonify(result), 500

@app.route('/api/containers/stop', methods=['POST'])
def stop_containers():
    """Stop Hublink containers"""
    logger.info("Stop containers requested")
    result = hublink_manager.stop_containers()
    if result.get("success"):
        return jsonify(result), 200
    else:
        return jsonify(result), 500

@app.route('/api/containers/restart', methods=['POST'])
def restart_containers():
    """Restart Hublink containers"""
    logger.info("Restart containers requested")
    result = hublink_manager.restart_containers()
    if result.get("success"):
        return jsonify(result), 200
    else:
        return jsonify(result), 500

@app.route('/api/logs')
def get_logs():
    """Get latest Docker Compose logs"""
    try:
        logger.debug("Logs requested")
        
        # Get the last 20 lines of docker-compose logs (only hublink-gateway service)
        result = hublink_manager._run_docker_command(f"docker compose -f {hublink_manager.compose_file} logs hublink-gateway --tail=20", timeout=10)
        
        if result and result.returncode == 0:
            logs = result.stdout.strip()
            if not logs:
                logs = "No logs available"
            return jsonify({
                "success": True,
                "logs": logs,
                "timestamp": time.time()
            })
        else:
            error_msg = result.stderr if result and result.stderr else "Failed to retrieve logs"
            return jsonify({
                "success": False,
                "error": error_msg,
                "timestamp": time.time()
            }), 500
            
    except Exception as e:
        logger.error(f"Error getting logs: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": time.time()
        }), 500

@app.route('/api/autofix/status')
def get_autofix_status():
    """Get auto-fix status"""
    global auto_fix_enabled
    return jsonify({
        "enabled": auto_fix_enabled,
        "timestamp": time.time()
    })

@app.route('/api/autofix/toggle', methods=['POST'])
def toggle_autofix():
    """Toggle auto-fix on/off"""
    global auto_fix_enabled
    try:
        data = request.get_json()
        if data and 'enabled' in data:
            auto_fix_enabled = bool(data['enabled'])
            logger.info(f"Auto-fix {'enabled' if auto_fix_enabled else 'disabled'}")
            return jsonify({
                "success": True,
                "enabled": auto_fix_enabled,
                "message": f"Auto-fix {'enabled' if auto_fix_enabled else 'disabled'}"
            })
        else:
            return jsonify({"error": "Missing 'enabled' parameter"}), 400
    except Exception as e:
        logger.error(f"Error toggling auto-fix: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/test/ble-error', methods=['POST'])
def test_ble_error():
    """Test endpoint to simulate BLE error for testing auto-fix routine"""
    try:
        logger.info("BLE error test triggered - simulating BLE error")
        
        # Simulate BLE error by creating a mock error response
        mock_errors = {
            "ble": "BLE device connectivity issue - TEST SIMULATION"
        }
        
        # Trigger the auto-fix routine with the mock error
        auto_fix_applied = auto_fix_manager.check_and_fix_issues(
            container_state={"state": "running", "containers": [{"status": "Up 5 minutes (healthy)"}]},
            container_errors=mock_errors,
            app_internet=True,
            hublink_internet=True
        )
        
        return jsonify({
            "success": True,
            "message": "BLE error simulation triggered",
            "auto_fix_applied": auto_fix_applied,
            "simulated_errors": mock_errors
        })
        
    except Exception as e:
        logger.error(f"Error in BLE error test: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# Removed /api/internet/check endpoint as it was causing duplicate requests to Hublink /status
# and is not used by the frontend

@app.errorhandler(404)
def not_found(error):
    logger.warning(f"404 error: {request.url}")
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"500 error: {error}")
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    import os
    logger.info("Starting Hublink Hypervisor")
    logger.info(f"Process ID: {os.getpid()}")
    logger.info(f"Hublink path: {HUBLINK_PATH}")
    logger.info(f"Compose file: {hublink_manager.compose_file}")
    
    app.run(
        host='0.0.0.0',
        port=8081,
        debug=IS_DEVELOPMENT  # Only enable debug mode in development
    ) 