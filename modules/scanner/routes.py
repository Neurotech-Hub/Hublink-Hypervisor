"""
Scanner API Routes
Provides REST API endpoints for Bluetooth scanner functionality
"""

import asyncio
import json
import logging
from datetime import datetime
from flask import Blueprint, jsonify, request
from .scanner import scanner_instance, SIMULATION_MODE

# Configure logging
logger = logging.getLogger(__name__)

# Create blueprint
scanner_bp = Blueprint('scanner', __name__, url_prefix='/api/scanner')

_scanner_loop = None
_scanner_loop_thread = None

def _ensure_background_loop():
    """Start and return a dedicated asyncio loop running in a background thread.
    Ensures all BLE coroutines run on the same loop to avoid cross-loop Futures.
    """
    global _scanner_loop, _scanner_loop_thread
    if _scanner_loop and _scanner_loop.is_running():
        return _scanner_loop

    import threading

    def loop_runner(loop: asyncio.AbstractEventLoop):
        asyncio.set_event_loop(loop)
        loop.run_forever()

    _scanner_loop = asyncio.new_event_loop()
    _scanner_loop_thread = threading.Thread(target=loop_runner, args=(_scanner_loop,), daemon=True)
    _scanner_loop_thread.start()
    return _scanner_loop

def run_async(coro):
    """Submit coroutine to dedicated scanner loop and wait for result."""
    loop = _ensure_background_loop()
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result()

@scanner_bp.route('/status', methods=['GET'])
def get_scanner_status():
    """Get current scanner status"""
    try:
        logger.debug("Scanner status requested")
        status = scanner_instance.get_status()
        return jsonify({
            "success": True,
            "status": status
        })
    except Exception as e:
        logger.error(f"Error getting scanner status: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@scanner_bp.route('/start', methods=['POST'])
def start_scan():
    """Start scanning for devices with optional name filter"""
    try:
        data = request.get_json() or {}
        device_name_filter = data.get('device_name_filter', 'Hublink')
        
        logger.info(f"Start scan requested with filter: '{device_name_filter}'")
        result = run_async(scanner_instance.start_scan(device_name_filter))
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error starting scan: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@scanner_bp.route('/stop', methods=['POST'])
def stop_scan():
    """Stop scanning for devices"""
    try:
        logger.info("Stop scan requested")
        result = run_async(scanner_instance.stop_scan())
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error stopping scan: {e}")
        # Ensure scanner state is reset even if there's an error
        scanner_instance.is_scanning = False
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@scanner_bp.route('/devices', methods=['GET'])
def get_devices():
    """Get list of discovered devices"""
    try:
        logger.debug("Device list requested")
        devices = scanner_instance.get_devices()
        return jsonify({
            "success": True,
            "devices": devices,
            "count": len(devices)
        })
    except Exception as e:
        logger.error(f"Error getting devices: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@scanner_bp.route('/device/<address>', methods=['GET'])
def get_device(address):
    """Get specific device by address"""
    try:
        logger.debug(f"Device info requested for {address}")
        device = scanner_instance.get_device(address)
        if device:
            return jsonify({
                "success": True,
                "device": device
            })
        else:
            return jsonify({
                "success": False,
                "error": "Device not found"
            }), 404
    except Exception as e:
        logger.error(f"Error getting device {address}: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@scanner_bp.route('/connect/<address>', methods=['POST'])
def connect_device(address):
    """Connect to a specific device"""
    try:
        logger.info(f"Connect to device requested: {address}")
        # The connect_to_device method will handle stopping the scan
        result = run_async(scanner_instance.connect_to_device(address))
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error connecting to device {address}: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@scanner_bp.route('/disconnect/<address>', methods=['POST'])
def disconnect_device(address):
    """Disconnect from a specific device"""
    try:
        logger.info(f"Disconnect from device requested: {address}")
        result = run_async(scanner_instance.disconnect_from_device(address))
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error disconnecting from device {address}: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@scanner_bp.route('/disconnect-all', methods=['POST'])
def disconnect_all_devices():
    """Disconnect from all connected devices"""
    try:
        logger.info("Disconnect all devices requested")
        result = run_async(scanner_instance.disconnect_all())
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error disconnecting all devices: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@scanner_bp.route('/test', methods=['POST'])
def test_scanner():
    """Test endpoint to verify scanner functionality"""
    try:
        logger.info("Scanner test requested")
        status = scanner_instance.get_status()
        return jsonify({
            "success": True,
            "message": "Scanner module is working",
            "status": status
        })
    except Exception as e:
        logger.error(f"Scanner test failed: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@scanner_bp.route('/simulate/connect/<address>', methods=['POST'])
def simulate_connect_device(address):
    """Simulate connecting to a device for development"""
    try:
        logger.info(f"Simulating connection to device: {address}")
        # Stop scanning to mirror real behavior
        try:
            run_async(scanner_instance.stop_scan())
        except Exception:
            pass
        
        # Find the device
        device = scanner_instance.get_device(address)
        if not device:
            return jsonify({
                "success": False,
                "error": "Device not found"
            }), 404
        
        # Enforce single connection - disconnect any existing connections
        if scanner_instance.connected_devices:
            logger.info("Disconnecting existing device to enforce single connection")
            for existing_address in list(scanner_instance.connected_devices.keys()):
                existing_device = scanner_instance.get_device(existing_address)
                if existing_device:
                    existing_device['connection_status'] = 'discovered'
                    existing_device['disconnected_at'] = datetime.now().isoformat()
            scanner_instance.connected_devices.clear()
        
        # Simulate connection
        device['connection_status'] = 'connected'
        device['connected_at'] = datetime.now().isoformat()
        
        # Add to connected devices (simulate)
        scanner_instance.connected_devices[address] = None  # Mock client
        
        logger.info(f"Simulated connection to {device['name']}")
        return jsonify({
            "success": True,
            "message": f"Simulated connection to {device['name']}",
            "device": device
        })
        
    except Exception as e:
        logger.error(f"Error simulating connection: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@scanner_bp.route('/simulate/disconnect/<address>', methods=['POST'])
def simulate_disconnect_device(address):
    """Simulate disconnecting from a device for development"""
    try:
        logger.info(f"Simulating disconnection from device: {address}")
        
        # Find the device
        device = scanner_instance.get_device(address)
        if not device:
            return jsonify({
                "success": False,
                "error": "Device not found"
            }), 404
        
        # Simulate disconnection
        device['connection_status'] = 'discovered'
        device['disconnected_at'] = datetime.now().isoformat()
        
        # Remove from connected devices
        if address in scanner_instance.connected_devices:
            del scanner_instance.connected_devices[address]
        
        logger.info(f"Simulated disconnection from {device['name']}")
        return jsonify({
            "success": True,
            "message": f"Simulated disconnection from {device['name']}",
            "device": device
        })
        
    except Exception as e:
        logger.error(f"Error simulating disconnection: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@scanner_bp.route('/read-node/<address>', methods=['POST'])
def read_node_characteristic(address):
    """Read the node characteristic data from a connected device"""
    try:
        logger.info(f"Reading node characteristic from device: {address}")
        
        # Check if device is connected
        if address not in scanner_instance.connected_devices:
            return jsonify({
                "success": False,
                "error": "Device not connected"
            }), 400
        
        # In simulation mode, return mock data
        if SIMULATION_MODE:
            mock_node_data = {
                "device_name": "Hublink Gateway",
                "firmware_version": "1.2.3",
                "upload_path": "/data/uploads",
                "status": "ready",
                "last_upload": "2025-08-14T15:30:00Z",
                "storage_available": "2.5GB",
                "connected_sensors": 3
            }
            
            return jsonify({
                "success": True,
                "data": json.dumps(mock_node_data, indent=2)
            })
        
        # In production, read from actual BLE characteristic on dedicated loop
        result = run_async(scanner_instance.read_node_characteristic(address))
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error reading node characteristic: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@scanner_bp.route('/write-gateway/<address>', methods=['POST'])
def write_gateway_command(address):
    """Write a command to the gateway characteristic"""
    try:
        data = request.get_json()
        if not data or 'command' not in data:
            return jsonify({
                "success": False,
                "error": "Command is required"
            }), 400
        
        command = data['command']
        logger.info(f"Writing gateway command to device {address}: {command}")
        
        # Check if device is connected
        if address not in scanner_instance.connected_devices:
            return jsonify({
                "success": False,
                "error": "Device not connected"
            }), 400
        
        # In simulation mode, just log the command
        if SIMULATION_MODE:
            logger.info(f"Simulation: Would write command '{command}' to gateway characteristic")
            return jsonify({
                "success": True,
                "message": f"Simulated command sent: {command}"
            })
        
        # In production, write to actual BLE characteristic on dedicated loop
        result = run_async(scanner_instance.write_gateway_command(address, command))
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error writing gateway command: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
