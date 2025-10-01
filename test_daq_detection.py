#!/usr/bin/env python3
"""
Test script to detect DAQ devices on Ubuntu
"""

import sys

def test_usb_detection():
    """Test USB device detection"""
    print("=== USB Device Detection Test ===")
    
    try:
        import usb.core
        import usb.util
        print("✓ pyusb library available")
        
        # List all USB devices
        devices = usb.core.find(find_all=True)
        device_list = list(devices)
        print(f"✓ Found {len(device_list)} USB devices total")
        
        # Check for common DAQ vendor IDs
        daq_vendors = {
            0x09db: "Measurement Computing",
            0x3923: "National Instruments", 
            0x13d3: "Advantech",
            0x10c4: "Silicon Labs",
            0x0403: "FTDI",
            0x0683: "Measurement Computing (alternative)"
        }
        
        print("\nDAQ device scan:")
        found_daq = False
        for device in device_list:
            vendor_id = device.idVendor
            product_id = device.idProduct
            
            if vendor_id in daq_vendors:
                print(f"✓ FOUND DAQ: {daq_vendors[vendor_id]} (VID: {vendor_id:04x}, PID: {product_id:04x})")
                found_daq = True
                
                # Try to get device info
                try:
                    manufacturer = usb.util.get_string(device, device.iManufacturer)
                    product = usb.util.get_string(device, device.iProduct)
                    print(f"  Manufacturer: {manufacturer}")
                    print(f"  Product: {product}")
                except:
                    print("  (Could not read device strings)")
        
        if not found_daq:
            print("✗ No DAQ devices detected with known vendor IDs")
            print("\nAll USB devices:")
            for device in device_list:
                print(f"  VID: {device.idVendor:04x}, PID: {device.idProduct:04x}")
        
    except ImportError:
        print("✗ pyusb not available - install with: pip3 install pyusb")
        return False
    except Exception as e:
        print(f"✗ USB detection error: {e}")
        return False
    
    return True

def test_serial_detection():
    """Test serial device detection"""
    print("\n=== Serial Device Detection Test ===")
    
    try:
        import serial.tools.list_ports
        print("✓ pyserial library available")
        
        ports = serial.tools.list_ports.comports()
        print(f"✓ Found {len(ports)} serial ports")
        
        if ports:
            for port in ports:
                print(f"  Port: {port.device}")
                print(f"    Description: {port.description}")
                print(f"    Hardware ID: {port.hwid}")
                
                # Check for DAQ-related keywords
                desc_lower = port.description.lower()
                if any(keyword in desc_lower for keyword in ['daq', 'data acquisition', 'measurement', 'usb serial']):
                    print(f"    *** Potential DAQ device ***")
                print()
        else:
            print("✗ No serial ports detected")
        
    except ImportError:
        print("✗ pyserial not available - install with: pip3 install pyserial")
        return False
    except Exception as e:
        print(f"✗ Serial detection error: {e}")
        return False
    
    return True

def test_permissions():
    """Test USB permissions"""
    print("=== Permission Test ===")
    
    import os
    import grp
    
    # Check group memberships
    groups = [grp.getgrgid(g).gr_name for g in os.getgroups()]
    print(f"User groups: {', '.join(groups)}")
    
    required_groups = ['plugdev', 'dialout']
    for group in required_groups:
        if group in groups:
            print(f"✓ User is in {group} group")
        else:
            print(f"✗ User NOT in {group} group")
    
    return True

def main():
    """Run all tests"""
    print("DAQ Device Detection Test for Ubuntu")
    print("=" * 50)
    
    # Test basic library availability
    print("Testing library imports...")
    try:
        import usb.core
        print("✓ pyusb available")
    except ImportError:
        print("✗ pyusb missing - run: pip3 install pyusb")
    
    try:
        import serial.tools.list_ports
        print("✓ pyserial available")
    except ImportError:
        print("✗ pyserial missing - run: pip3 install pyserial")
    
    print()
    
    # Run detection tests
    test_usb_detection()
    test_serial_detection()
    test_permissions()
    
    print("\n" + "=" * 50)
    print("If no DAQ devices were found:")
    print("1. Make sure your DAQ device is connected via USB")
    print("2. Run the installation script: bash install_ubuntu_daq.sh")
    print("3. Reboot your system")
    print("4. Run this test again")
    print("")
    print("Common DAQ device troubleshooting:")
    print("- Check 'lsusb' output for your device")
    print("- Check 'dmesg | tail' for USB connection messages")
    print("- Try running with sudo for permission testing")

if __name__ == "__main__":
    main()