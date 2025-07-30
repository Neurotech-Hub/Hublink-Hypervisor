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

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('hublink_hypervisor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for development

# Configuration
HUBLINK_PATH = '/opt/hublink'
DOCKER_COMPOSE_FILE = 'docker-compose.yml'
DOCKER_COMPOSE_MAC_FILE = 'docker-compose.macos.yml'

def get_hublink_port():
    """Determine the correct port for Hublink container based on OS"""
    system = platform.system().lower()
    if system == "darwin":  # macOS
        return 6000
    else:  # Linux (production)
        return 5000

HUBLINK_PORT = get_hublink_port()
logger.info(f"Detected OS: {platform.system()}, using Hublink port: {HUBLINK_PORT}")

class HublinkManager:
    """Manages Hublink Docker container operations and status monitoring"""
    
    def __init__(self):
        self.hublink_path = HUBLINK_PATH
        self.compose_file = self._get_compose_file()
        logger.info(f"Initialized HublinkManager with path: {self.hublink_path}")
        logger.info(f"Using compose file: {self.compose_file}")
    
    def _get_compose_file(self):
        """Determine which docker-compose file to use based on OS"""
        system = platform.system().lower()
        
        if system == "darwin":  # macOS
            if os.path.exists(os.path.join(self.hublink_path, DOCKER_COMPOSE_MAC_FILE)):
                logger.debug("Detected macOS environment, using docker-compose.macos.yml")
                return DOCKER_COMPOSE_MAC_FILE
            else:
                logger.warning("macOS detected but docker-compose.macos.yml not found, falling back to docker-compose.yml")
                return DOCKER_COMPOSE_FILE
        else:  # Linux (production)
            if os.path.exists(os.path.join(self.hublink_path, DOCKER_COMPOSE_FILE)):
                logger.debug("Detected Linux environment, using docker-compose.yml")
                return DOCKER_COMPOSE_FILE
            else:
                logger.error(f"No docker-compose.yml found in {self.hublink_path}")
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
            logger.debug("Fetching container status")
            
            # Get all containers with simple format
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
            
            # Check for active Hublink containers (exclude watchtower and exited containers)
            hublink_containers = [
                c for c in containers 
                if 'hublink' in c['name'].lower() 
                and 'watchtower' not in c['name'].lower()
                and 'Exited' not in c['status']
            ]
            
            logger.debug(f"Found {len(hublink_containers)} Hublink containers")
            logger.debug(f"All containers: {[c['name'] for c in containers]}")
            logger.debug(f"Hublink containers: {[c['name'] for c in hublink_containers]}")
            return {
                "containers": containers,
                "hublink_containers": hublink_containers,
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"Error getting container status: {e}")
            return {"error": str(e)}
    
    def get_container_state(self):
        """Get simplified container state for UI"""
        try:
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
            
            # Check if any container is running
            running_containers = [c for c in hublink_containers if "Up" in c["status"]]
            
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
            result = self._run_docker_command(f"docker-compose -f {self.compose_file} up -d", timeout=60)
            
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
            result = self._run_docker_command(f"docker-compose -f {self.compose_file} down", timeout=45)
            
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
            logger.debug("Checking app internet connectivity")
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
                        logger.debug(f"App has internet connectivity via {endpoint}")
                        return True
                except Exception as e:
                    logger.debug(f"Failed to connect to {endpoint}: {e}")
                    continue
            
            logger.warning("App internet check failed for all endpoints")
            return False
        except Exception as e:
            logger.error(f"App internet check failed: {e}")
            return False
    
    @staticmethod
    def check_hublink_internet():
        """Check if Hublink container has internet connectivity"""
        try:
            logger.debug("Checking Hublink container internet connectivity")
            
            # Check container on the appropriate port
            try:
                response = requests.get(f"http://localhost:{HUBLINK_PORT}/health", timeout=3)
                if response.status_code == 200:
                    logger.debug(f"Hublink container has internet connectivity via port {HUBLINK_PORT}")
                    return True
                else:
                    logger.warning(f"Hublink container health check failed with status: {response.status_code}")
                    return False
            except requests.exceptions.RequestException:
                logger.warning("Hublink container health check failed - connection refused")
                return False
            

            
        except Exception as e:
            logger.error(f"Hublink container internet check failed: {e}")
            return False

# Initialize managers
hublink_manager = HublinkManager()
internet_checker = InternetChecker()

@app.route('/')
def index():
    """Main dashboard page"""
    logger.debug("Serving main dashboard")
    return render_template('index.html')

@app.route('/api/health')
def health():
    """Health check endpoint"""
    logger.debug("Health check requested")
    return jsonify({
        "status": "ok",
        "timestamp": time.time(),
        "service": "hublink-hypervisor"
    })

@app.route('/api/status')
def status():
    """Get comprehensive system status"""
    try:
        logger.debug("Status check requested")
        
        # Get container state
        container_state = hublink_manager.get_container_state()
        
        # Check internet connectivity
        app_internet = internet_checker.check_app_internet()
        hublink_internet = internet_checker.check_hublink_internet()
        
        # Determine overall status
        errors = {}
        timestamps = {}
        
        if "error" in container_state:
            errors["container"] = container_state["error"]
            timestamps["container"] = time.time()
        
        if not app_internet:
            errors["app_internet"] = "Hypervisor app has no internet connectivity"
            timestamps["app_internet"] = time.time()
        
        if container_state.get("state") == "running" and not hublink_internet:
            errors["hublink_internet"] = "Hublink container has no internet connectivity"
            timestamps["hublink_internet"] = time.time()
        
        # Check Hublink API status if container is running
        hublink_status = None
        secret_url = None
        gateway_name = None
        if container_state.get("state") == "running":
            try:
                response = requests.get(f"http://localhost:{HUBLINK_PORT}/status", timeout=3)
                if response.status_code in [200, 500]:  # Accept both 200 and 500 as valid responses
                    hublink_status = response.json()
                    logger.debug(f"Hublink API connected via port {HUBLINK_PORT}")
                    # Get secret_url and gateway_name if available
                    secret_url = hublink_status.get("secret_url")
                    gateway_name = hublink_status.get("gateway_name")
                    # Merge any Hublink errors
                    if hublink_status.get("status") == "error":
                        errors.update(hublink_status.get("errors", {}))
                        timestamps.update(hublink_status.get("timestamps", {}))
                else:
                    errors["hublink_api"] = f"Hublink API returned status {response.status_code}"
                    timestamps["hublink_api"] = time.time()
            except Exception as e:
                errors["hublink_api"] = f"Failed to connect to Hublink API: {str(e)}"
                timestamps["hublink_api"] = time.time()
        
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
                "timestamp": time.time()
            }
        
        logger.debug(f"Status response: {status_response}")
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
        
        # Get the last 20 lines of docker-compose logs
        result = hublink_manager._run_docker_command("docker-compose -f docker-compose.macos.yml logs --tail=20", timeout=10)
        
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

@app.route('/api/internet/check')
def check_internet():
    """Check internet connectivity"""
    logger.debug("Internet connectivity check requested")
    return jsonify({
        "app_internet": internet_checker.check_app_internet(),
        "hublink_internet": internet_checker.check_hublink_internet(),
        "timestamp": time.time()
    })

@app.errorhandler(404)
def not_found(error):
    logger.warning(f"404 error: {request.url}")
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"500 error: {error}")
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    logger.info("Starting Hublink Hypervisor")
    logger.info(f"Hublink path: {HUBLINK_PATH}")
    logger.info(f"Compose file: {hublink_manager.compose_file}")
    
    app.run(
        host='0.0.0.0',
        port=8081,
        debug=True
    ) 