#!/usr/bin/env python3
"""
Test script for the Hublink Scanner module
"""

import asyncio
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_scanner():
    """Test the scanner module functionality"""
    try:
        print("Testing Hublink Scanner Module...")
        
        # Import scanner module
        from modules.scanner.scanner import scanner_instance
        
        print("✓ Scanner module imported successfully")
        
        # Test scanner status
        status = scanner_instance.get_status()
        print(f"✓ Scanner status: {status}")
        
        # Test getting devices (should be empty initially)
        devices = scanner_instance.get_devices()
        print(f"✓ Initial devices: {len(devices)} found")
        
        print("\nScanner module test completed successfully!")
        print("\nNote: This test only verifies the module loads correctly.")
        print("To test actual Bluetooth scanning, you'll need:")
        print("- Bluetooth hardware available")
        print("- Hublink devices nearby")
        print("- Proper permissions (especially on macOS)")
        
    except ImportError as e:
        print(f"✗ Failed to import scanner module: {e}")
        print("Make sure you have installed the required dependencies:")
        print("pip install bleak")
        return False
    except Exception as e:
        print(f"✗ Scanner test failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = asyncio.run(test_scanner())
    sys.exit(0 if success else 1)
