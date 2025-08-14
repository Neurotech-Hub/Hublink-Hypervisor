#!/usr/bin/env python3
"""
Test script to demonstrate the scanner simulation
"""

import requests
import time
import json

BASE_URL = "http://localhost:8081"

def test_simulation():
    """Test the scanner simulation"""
    print("🔧 Hublink Scanner Simulation Demo")
    print("=" * 50)
    
    # Test 1: Check initial state
    print("\n1. Initial state (2 devices discovered, 0 connected)")
    response = requests.get(f"{BASE_URL}/api/scanner/status")
    if response.status_code == 200:
        status = response.json()['status']
        print(f"   ✓ Devices discovered: {status['discovered_count']}")
        print(f"   ✓ Devices connected: {status['connected_count']}")
        
        for device in status['devices']:
            print(f"   - {device['name']} ({device['address']}) - {device['connection_status']}")
    else:
        print(f"   ✗ Failed to get status: {response.status_code}")
        return
    
    # Test 2: Connect to first device
    print("\n2. Connecting to Hublink Gateway #1...")
    response = requests.post(f"{BASE_URL}/api/scanner/simulate/connect/AA:BB:CC:DD:EE:FF")
    if response.status_code == 200:
        result = response.json()
        print(f"   ✓ {result['message']}")
    else:
        print(f"   ✗ Failed to connect: {response.status_code}")
        return
    
    # Test 3: Check connected state
    print("\n3. After connection (1 device connected)")
    response = requests.get(f"{BASE_URL}/api/scanner/status")
    if response.status_code == 200:
        status = response.json()['status']
        print(f"   ✓ Devices discovered: {status['discovered_count']}")
        print(f"   ✓ Devices connected: {status['connected_count']}")
        
        for device in status['devices']:
            print(f"   - {device['name']} ({device['address']}) - {device['connection_status']}")
    else:
        print(f"   ✗ Failed to get status: {response.status_code}")
        return
    
    # Test 4: Connect to second device
    print("\n4. Connecting to Hublink Gateway #2...")
    response = requests.post(f"{BASE_URL}/api/scanner/simulate/connect/11:22:33:44:55:66")
    if response.status_code == 200:
        result = response.json()
        print(f"   ✓ {result['message']}")
    else:
        print(f"   ✗ Failed to connect: {response.status_code}")
        return
    
    # Test 5: Check both connected state
    print("\n5. After both connections (2 devices connected)")
    response = requests.get(f"{BASE_URL}/api/scanner/status")
    if response.status_code == 200:
        status = response.json()['status']
        print(f"   ✓ Devices discovered: {status['discovered_count']}")
        print(f"   ✓ Devices connected: {status['connected_count']}")
        
        for device in status['devices']:
            print(f"   - {device['name']} ({device['address']}) - {device['connection_status']}")
    else:
        print(f"   ✗ Failed to get status: {response.status_code}")
        return
    
    # Test 6: Disconnect from first device
    print("\n6. Disconnecting from Hublink Gateway #1...")
    response = requests.post(f"{BASE_URL}/api/scanner/simulate/disconnect/AA:BB:CC:DD:EE:FF")
    if response.status_code == 200:
        result = response.json()
        print(f"   ✓ {result['message']}")
    else:
        print(f"   ✗ Failed to disconnect: {response.status_code}")
        return
    
    # Test 7: Check final state
    print("\n7. Final state (1 device connected)")
    response = requests.get(f"{BASE_URL}/api/scanner/status")
    if response.status_code == 200:
        status = response.json()['status']
        print(f"   ✓ Devices discovered: {status['discovered_count']}")
        print(f"   ✓ Devices connected: {status['connected_count']}")
        
        for device in status['devices']:
            print(f"   - {device['name']} ({device['address']}) - {device['connection_status']}")
    else:
        print(f"   ✗ Failed to get status: {response.status_code}")
        return
    
    print("\n✅ Simulation demo completed!")
    print("\n📱 Access the web interface at: http://localhost:8081")
    print("   Go to the 'Scanner' tab to see the interface with example devices")
    print("   You can click 'Connect' and 'Disconnect' buttons to see the changes")

if __name__ == "__main__":
    try:
        test_simulation()
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to the hypervisor. Make sure it's running:")
        print("   docker ps | grep hublink-hypervisor")
    except Exception as e:
        print(f"❌ Error: {e}")
