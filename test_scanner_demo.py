#!/usr/bin/env python3
"""
Demo script to test the scanner functionality
"""

import requests
import time
import json

BASE_URL = "http://localhost:8081"

def test_scanner_demo():
    """Demo the scanner functionality"""
    print("🔍 Hublink Scanner Demo")
    print("=" * 50)
    
    # Test 1: Check scanner status
    print("\n1. Checking scanner status...")
    response = requests.get(f"{BASE_URL}/api/scanner/status")
    if response.status_code == 200:
        status = response.json()
        print(f"   ✓ Scanner ready: {status['status']['is_scanning']}")
        print(f"   ✓ Devices found: {status['status']['discovered_count']}")
    else:
        print(f"   ✗ Failed to get status: {response.status_code}")
        return
    
    # Test 2: Start scanning
    print("\n2. Starting 10-second scan...")
    response = requests.post(f"{BASE_URL}/api/scanner/start")
    if response.status_code == 200:
        result = response.json()
        print(f"   ✓ Scan started: {result.get('message', 'Success')}")
    else:
        print(f"   ✗ Failed to start scan: {response.status_code}")
        return
    
    # Test 3: Monitor scan progress
    print("\n3. Monitoring scan progress...")
    for i in range(6):  # Check 6 times over 10 seconds
        time.sleep(2)
        response = requests.get(f"{BASE_URL}/api/scanner/status")
        if response.status_code == 200:
            status = response.json()['status']
            print(f"   {i*2}s: Scanning={status['is_scanning']}, Devices={status['discovered_count']}")
        else:
            print(f"   ✗ Failed to get status")
    
    # Test 4: Check final status
    print("\n4. Final scan results...")
    response = requests.get(f"{BASE_URL}/api/scanner/status")
    if response.status_code == 200:
        status = response.json()['status']
        print(f"   ✓ Scan completed: {not status['is_scanning']}")
        print(f"   ✓ Devices discovered: {status['discovered_count']}")
        
        if status['devices']:
            print("\n   Discovered devices:")
            for device in status['devices']:
                print(f"   - {device['name']} ({device['address']})")
                print(f"     RSSI: {device['rssi']} dBm")
                print(f"     Upload Path: {device['upload_path']}")
        else:
            print("   No Hublink devices found (expected in development)")
    else:
        print(f"   ✗ Failed to get final status")
    
    print("\n✅ Demo completed!")
    print("\n📱 Access the web interface at: http://localhost:8081")
    print("   Go to the 'Scanner' tab to see the interface")

if __name__ == "__main__":
    try:
        test_scanner_demo()
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to the hypervisor. Make sure it's running:")
        print("   docker ps | grep hublink-hypervisor")
    except Exception as e:
        print(f"❌ Error: {e}")
