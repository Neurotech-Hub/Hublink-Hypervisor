"""
Bluetooth Scanner for Hublink Devices
Uses Bleak for cross-platform Bluetooth Low Energy scanning
"""

import asyncio
import json
import logging
import warnings
from typing import Dict, List, Optional, Callable
from datetime import datetime
from bleak import BleakScanner, BleakClient, BleakError
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

# Configure logging
logger = logging.getLogger(__name__)

# Hublink BLE UUIDs
SERVICE_UUID = "57617368-5501-0001-8000-00805f9b34fb"
CHARACTERISTIC_UUID_FILENAME = "57617368-5502-0001-8000-00805f9b34fb"
CHARACTERISTIC_UUID_FILETRANSFER = "57617368-5503-0001-8000-00805f9b34fb"
CHARACTERISTIC_UUID_GATEWAY = "57617368-5504-0001-8000-00805f9b34fb"
CHARACTERISTIC_UUID_NODE = "57617368-5505-0001-8000-00805f9b34fb"

class BluetoothScanner:
    """Manages Bluetooth Low Energy scanning for Hublink devices"""
    
    def __init__(self):
        self.scanner = None  # Will be created per scan
        self.discovered_devices: Dict[str, Dict] = {}
        self.connected_devices: Dict[str, BleakClient] = {}
        self.is_scanning = False
        self.scan_start_time: Optional[datetime] = None
        self._status_callback: Optional[Callable] = None
        self.device_name_filter: str = "Hublink"  # Default filter
        
        logger.info("BluetoothScanner initialized")
    
    def _disconnection_callback(self, client: BleakClient):
        """Callback for when a device disconnects unexpectedly"""
        try:
            # Find which device this client belongs to
            disconnected_address = None
            for address, stored_client in self.connected_devices.items():
                if stored_client == client:
                    disconnected_address = address
                    break
            
            if disconnected_address:
                logger.warning(f"Device {disconnected_address} disconnected unexpectedly")
                
                # Update device info to reflect disconnection
                if disconnected_address in self.discovered_devices:
                    self.discovered_devices[disconnected_address]['connection_status'] = 'discovered'
                    self.discovered_devices[disconnected_address]['disconnected_at'] = datetime.now().isoformat()
                    self.discovered_devices[disconnected_address]['disconnect_reason'] = 'unexpected'
                
                # Remove from connected devices
                if disconnected_address in self.connected_devices:
                    del self.connected_devices[disconnected_address]
                
                # Notify status callback if set
                if self._status_callback:
                    self._status_callback('device_disconnected', {
                        'address': disconnected_address,
                        'reason': 'unexpected'
                    })
                
                logger.info(f"Cleaned up state for disconnected device {disconnected_address}")
            else:
                logger.warning("Received disconnection callback for unknown device")
                
        except Exception as e:
            logger.error(f"Error in disconnection callback: {e}")
    
    def set_status_callback(self, callback: Callable):
        """Set callback for status updates"""
        self._status_callback = callback

    def set_device_name_filter(self, filter_text: str):
        """Set the device name filter for scanning"""
        self.device_name_filter = filter_text.strip()
        logger.info(f"Device name filter set to: '{self.device_name_filter}'")
    


    def _detection_callback(self, device: BLEDevice, advertisement_data: AdvertisementData):
        """Callback for device detection during scanning"""
        try:
            # Log ALL devices discovered at debug level
            device_name = device.name or 'Unknown'
            logger.debug(f"BLE Device discovered: {device_name} ({device.address})")
            logger.debug(f"  Service UUIDs: {advertisement_data.service_uuids}")
            logger.debug(f"  RSSI: {device.rssi}")
            logger.debug(f"  Manufacturer Data: {advertisement_data.manufacturer_data}")
            
            # Filter devices by name using the configured filter
            if device.name and self.device_name_filter.lower() in device.name.lower():
                logger.info(f"Device match '{self.device_name_filter}': {device.name} ({device.address})")
                
                device_info = {
                    'address': device.address,
                    'name': device.name,
                    'rssi': device.rssi,
                    'discovered_at': datetime.now().isoformat(),
                    'advertisement_data': {
                        'manufacturer_data': advertisement_data.manufacturer_data,
                        'service_data': advertisement_data.service_data,
                        'service_uuids': advertisement_data.service_uuids
                    },
                    'upload_path': None,  # Will be populated when we connect
                    'connection_status': 'discovered'
                }
                
                # Update discovered devices
                self.discovered_devices[device.address] = device_info
                
                logger.info(f"Added to device list: {device.name} ({device.address})")
                
                # Notify status callback if set
                if self._status_callback:
                    self._status_callback('device_discovered', device_info)
            else:
                logger.debug(f"No match for filter '{self.device_name_filter}': {device_name} ({device.address})")
                
        except Exception as e:
            logger.error(f"Error in detection callback: {e}")
    
    async def start_scan(self, device_name_filter: str = None) -> Dict:
        """Start scanning for devices with optional name filter"""
        try:
            if self.is_scanning:
                return {"success": False, "error": "Scanner is already running"}
            
            # Set device name filter if provided
            if device_name_filter:
                self.set_device_name_filter(device_name_filter)
            
            logger.info(f"Starting Bluetooth scan for devices (filter: '{self.device_name_filter}')")
            self.is_scanning = True
            self.scan_start_time = datetime.now()
            
            # Clear previous discoveries (always, regardless of simulation mode)
            self.discovered_devices.clear()
            
            # In simulation mode, skip actual Bluetooth scan
            if SIMULATION_MODE:
                logger.info("Simulation mode: Skipping actual Bluetooth scan")
                return {"success": True, "message": "Scan started (simulation mode)"}
            
            # Create new scanner instance for this scan (like reference code)
            self.scanner = BleakScanner(detection_callback=self._detection_callback)
            
            # Start scanning - simple approach like reference code
            await self.scanner.start()
            logger.info("Bluetooth scan started successfully")
            return {"success": True, "message": "Scan started"}
            
        except Exception as e:
            logger.error(f"Error starting scan: {e}")
            self.is_scanning = False
            return {"success": False, "error": str(e)}
    
    async def stop_scan(self) -> Dict:
        """Stop scanning for devices"""
        try:
            if not self.is_scanning:
                # Idempotent: treat as success to simplify callers
                return {"success": True, "message": "Scanner already stopped"}
            
            logger.info("Stopping Bluetooth scan")
            
            # In simulation mode, just return success without actual scanning
            if SIMULATION_MODE:
                logger.info("Simulation mode: Skipping actual Bluetooth scan stop")
                self.is_scanning = False
                return {"success": True, "message": "Scan stopped (simulation mode)"}
            
            # Stop scanning - simple approach like reference code
            if self.scanner:
                await self.scanner.stop()
                self.scanner = None
            
            self.is_scanning = False
            
            logger.info("Bluetooth scan stopped successfully")
            return {"success": True, "message": "Scan stopped"}
            
        except Exception as e:
            logger.error(f"Error stopping scan: {e}")
            self.is_scanning = False
            if self.scanner:
                self.scanner = None
            return {"success": False, "error": str(e)}
    
    def get_devices(self) -> List[Dict]:
        """Get list of discovered devices"""
        return list(self.discovered_devices.values())
    
    def get_device(self, address: str) -> Optional[Dict]:
        """Get specific device by address"""
        return self.discovered_devices.get(address)
    
    async def connect_to_device(self, address: str) -> Dict:
        """Connect to a specific Hublink device"""
        try:
            if address not in self.discovered_devices:
                return {"success": False, "error": "Device not found"}
            
            if address in self.connected_devices:
                return {"success": False, "error": "Already connected to this device"}
            
            # Stop scanning immediately when connecting
            if self.is_scanning:
                logger.info("Stopping scan before connecting to device")
                await self.stop_scan()
            
            # Enforce single connection - disconnect any existing connections
            if self.connected_devices:
                logger.info("Disconnecting existing device to enforce single connection")
                await self.disconnect_all()
            
            device_info = self.discovered_devices[address]
            logger.info(f"Connecting to device: {device_info['name']} ({address})")
            
            # Create BleakClient and connect - use the same pattern as your working example
            client = BleakClient(address, timeout=5.0)
            
            # Set disconnection callback before connecting
            client.set_disconnected_callback(self._disconnection_callback)
            
            await client.connect()

            # Wait for service discovery like your working example
            if not client.services:
                logger.warning("No services found")
                await client.disconnect()
                return {"success": False, "error": "No services found"}
            
            logger.debug("Services discovered successfully")
            
            # Small stabilization delay like your working example
            await asyncio.sleep(0.1)
            
            # Update device info with connection status
            device_info['connection_status'] = 'connected'
            device_info['connected_at'] = datetime.now().isoformat()
            
            # Try to read node information
            try:
                node_data = await client.read_gatt_char(CHARACTERISTIC_UUID_NODE)
                data_str = node_data.decode('utf-8')
                node_info = json.loads(data_str)
                device_info['upload_path'] = node_info.get('upload_path', 'Unknown')
                device_info['node_data_raw'] = data_str  # Store raw data for display
                logger.info(f"Device upload path: {device_info['upload_path']}")
            except Exception as e:
                logger.warning(f"Could not read node info from {address}: {e}")
                device_info['upload_path'] = 'Unknown'
                device_info['node_data_raw'] = None
            
            # Store connected client
            self.connected_devices[address] = client
            
            logger.info(f"Successfully connected to {device_info['name']}")
            return {
                "success": True, 
                "message": f"Connected to {device_info['name']}",
                "device": device_info
            }
            
        except Exception as e:
            logger.error(f"Error connecting to device {address}: {e}")
            return {"success": False, "error": str(e)}
    
    async def disconnect_from_device(self, address: str) -> Dict:
        """Disconnect from a specific device"""
        try:
            if address not in self.connected_devices:
                return {"success": False, "error": "Not connected to this device"}
            
            device_info = self.discovered_devices.get(address, {})
            logger.info(f"Disconnecting from device: {device_info.get('name', address)}")
            
            # Disconnect client
            client = self.connected_devices[address]
            await client.disconnect()
            
            # Remove from connected devices
            del self.connected_devices[address]
            
            # Update device info
            if address in self.discovered_devices:
                self.discovered_devices[address]['connection_status'] = 'discovered'
                self.discovered_devices[address]['disconnected_at'] = datetime.now().isoformat()
                self.discovered_devices[address]['disconnect_reason'] = 'manual'
            
            logger.info(f"Successfully disconnected from {device_info.get('name', address)}")
            return {"success": True, "message": "Disconnected successfully"}
            
        except Exception as e:
            logger.error(f"Error disconnecting from device {address}: {e}")
            return {"success": False, "error": str(e)}

    async def read_node_characteristic(self, address: str) -> Dict:
        """Read the node characteristic data from a connected device"""
        try:
            if address not in self.connected_devices:
                return {"success": False, "error": "Device not connected"}
            
            client = self.connected_devices[address]
            if not client:
                return {"success": False, "error": "No BLE client available"}
            
            # Verify client is still connected and services are available like your working example
            if not client.is_connected:
                # Clean up disconnected device from our state
                if address in self.connected_devices:
                    del self.connected_devices[address]
                if address in self.discovered_devices:
                    self.discovered_devices[address]['connection_status'] = 'discovered'
                    self.discovered_devices[address]['disconnected_at'] = datetime.now().isoformat()
                    self.discovered_devices[address]['disconnect_reason'] = 'timeout'
                logger.warning(f"Device {address} is no longer connected during read operation")
                return {"success": False, "error": "Device disconnected"}
            
            if not client.services:
                return {"success": False, "error": "No services available"}
            
            logger.info(f"Reading node characteristic from {address}")
            
            # Read the node characteristic directly like your working example
            node_data = await client.read_gatt_char(CHARACTERISTIC_UUID_NODE)
            data_str = node_data.decode('utf-8')
            
            logger.info(f"Successfully read node characteristic: {data_str}")
            return {
                "success": True,
                "data": data_str
            }
            
        except Exception as e:
            logger.error(f"Error reading node characteristic from {address}: {e}")
            return {"success": False, "error": str(e)}

    async def write_gateway_command(self, address: str, command: str) -> Dict:
        """Write a command to the gateway characteristic"""
        try:
            if address not in self.connected_devices:
                return {"success": False, "error": "Device not connected"}
            
            client = self.connected_devices[address]
            if not client:
                return {"success": False, "error": "No BLE client available"}
            
            # Verify client is still connected and services are available like your working example
            if not client.is_connected:
                # Clean up disconnected device from our state
                if address in self.connected_devices:
                    del self.connected_devices[address]
                if address in self.discovered_devices:
                    self.discovered_devices[address]['connection_status'] = 'discovered'
                    self.discovered_devices[address]['disconnected_at'] = datetime.now().isoformat()
                    self.discovered_devices[address]['disconnect_reason'] = 'timeout'
                logger.warning(f"Device {address} is no longer connected during write operation")
                return {"success": False, "error": "Device disconnected"}
            
            if not client.services:
                return {"success": False, "error": "No services available"}
            
            logger.info(f"Writing gateway command to {address}: {command}")
            
            # Write to the gateway characteristic directly like your working example
            command_bytes = command.encode('utf-8')
            await client.write_gatt_char(CHARACTERISTIC_UUID_GATEWAY, command_bytes, response=True)
            
            logger.info(f"Successfully wrote gateway command: {command}")
            return {
                "success": True,
                "message": f"Command sent: {command}"
            }
            
        except Exception as e:
            logger.error(f"Error writing gateway command to {address}: {e}")
            return {"success": False, "error": str(e)}
    
    async def disconnect_all(self) -> Dict:
        """Disconnect from all connected devices"""
        try:
            if not self.connected_devices:
                return {"success": True, "message": "No devices connected"}
            
            logger.info(f"Disconnecting from {len(self.connected_devices)} devices")
            
            for address, client in self.connected_devices.items():
                try:
                    await client.disconnect()
                    if address in self.discovered_devices:
                        self.discovered_devices[address]['connection_status'] = 'discovered'
                except Exception as e:
                    logger.warning(f"Error disconnecting from {address}: {e}")
            
            self.connected_devices.clear()
            
            logger.info("Disconnected from all devices")
            return {"success": True, "message": "Disconnected from all devices"}
            
        except Exception as e:
            logger.error(f"Error disconnecting from all devices: {e}")
            return {"success": False, "error": str(e)}

    def cleanup(self):
        """Clean up scanner resources"""
        try:
            logger.info("Cleaning up scanner resources")
            self.is_scanning = False
            # Note: We can't easily clean up the scanner instance here due to async constraints
            # The scanner will be cleaned up when the process ends
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def get_status(self) -> Dict:
        """Get current scanner status"""
        return {
            "is_scanning": self.is_scanning,
            "scan_start_time": self.scan_start_time.isoformat() if self.scan_start_time else None,
            "discovered_count": len(self.discovered_devices),
            "connected_count": len(self.connected_devices),
            "devices": self.get_devices()
        }
    
    async def cleanup(self):
        """Cleanup resources"""
        try:
            # Stop scanning if running
            if self.is_scanning:
                await self.stop_scan()
            
            # Disconnect all devices
            await self.disconnect_all()
            
            logger.info("BluetoothScanner cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

# Global scanner instance
scanner_instance = BluetoothScanner()

# Development simulation mode
SIMULATION_MODE = False  # Set to True to show example devices

if SIMULATION_MODE:
    # Add some example devices for development
    example_devices = [
        {
            'address': 'AA:BB:CC:DD:EE:FF',
            'name': 'Hublink Gateway #1',
            'rssi': -45,
            'discovered_at': datetime.now().isoformat(),
            'advertisement_data': {
                'manufacturer_data': {},
                'service_data': {},
                'service_uuids': [SERVICE_UUID]
            },
            'upload_path': '/data/uploads',
            'connection_status': 'discovered'
        },
        {
            'address': '11:22:33:44:55:66',
            'name': 'Hublink Gateway #2',
            'rssi': -67,
            'discovered_at': datetime.now().isoformat(),
            'advertisement_data': {
                'manufacturer_data': {},
                'service_data': {},
                'service_uuids': [SERVICE_UUID]
            },
            'upload_path': '/home/hublink/data',
            'connection_status': 'discovered'
        }
    ]
    
    # Add example devices to the scanner
    for device in example_devices:
        scanner_instance.discovered_devices[device['address']] = device
    
    print("Simulation mode enabled - showing example Hublink devices")
