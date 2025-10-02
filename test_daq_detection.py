#!/usr/bin/env python3
"""
Test script to detect MCC DAQ devices using uldaq on Ubuntu
"""

import sys

def test_uldaq_detection():
    """Test uldaq MCC device detection"""
    print("=== MCC uldaq Device Detection Test ===")
    
    try:
        from uldaq import get_daq_device_inventory, DaqDevice, AiInputMode, Range
        print("✓ uldaq library available")
        
        # Get device inventory
        devices = get_daq_device_inventory()
        print(f"✓ Found {len(devices)} MCC DAQ devices")
        
        if devices:
            for i, descriptor in enumerate(devices):
                print(f"\nDevice {i+1}:")
                print(f"  Product Name: {descriptor.product_name}")
                print(f"  Product ID: {descriptor.product_id}")
                print(f"  Interface Type: {descriptor.interface_type}")
                print(f"  Device Type: {descriptor.dev_type}")
                
                # Try to connect and get info
                try:
                    device = DaqDevice(descriptor)
                    device.connect()
                    print(f"  Connection: ✓ Success")
                    
                    # Get AI info
                    ai_device = device.get_ai_device()
                    if ai_device:
                        ai_info = ai_device.get_info()
                        num_channels = ai_info.get_num_chans()
                        ranges = ai_info.get_ranges(AiInputMode.SINGLE_ENDED)
                        print(f"  Analog Inputs: {num_channels} channels")
                        print(f"  Voltage Ranges: {ranges}")
                        
                        # Test reading a channel
                        try:
                            voltage = ai_device.a_in(0, AiInputMode.SINGLE_ENDED, Range.BIP10VOLTS)
                            print(f"  Test Reading (CH0): {voltage:.3f} V")
                        except Exception as e:
                            print(f"  Test Reading: Failed - {e}")
                    
                    device.disconnect()
                    
                except Exception as e:
                    print(f"  Connection: ✗ Failed - {e}")
        else:
            print("✗ No MCC DAQ devices detected")
        
        return len(devices) > 0
        
    except ImportError:
        print("✗ uldaq not available")
        print("  Install with: pip3 install uldaq")
        print("  Also install C++ library: see install_ubuntu_daq.sh")
        return False
    except Exception as e:
        print(f"✗ uldaq detection error: {e}")
        return False
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
    print("MCC DAQ Device Detection Test for Ubuntu (using uldaq)")
    print("=" * 60)
    
    # Test basic library availability
    print("Testing library imports...")
    try:
        from uldaq import get_daq_device_inventory
        print("✓ uldaq available")
    except ImportError:
        print("✗ uldaq missing - run: pip3 install uldaq")
        print("  Also install C++ library with install_ubuntu_daq.sh")
    
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
    uldaq_found = test_uldaq_detection()
    test_usb_detection()
    test_serial_detection()
    test_permissions()
    
    print("\n" + "=" * 60)
    if uldaq_found:
        print("✓ SUCCESS: MCC DAQ device(s) detected with uldaq!")
        print("Your application should now work with real sensor data.")
    else:
        print("✗ No MCC DAQ devices found.")
        print("Troubleshooting steps:")
        print("1. Make sure your MCC DAQ device is connected via USB")
        print("2. Run the installation script: bash install_ubuntu_daq.sh")
        print("3. Reboot your system")
        print("4. Run this test again")
        print("5. Check 'lsusb | grep 09db' for MCC devices")

def test_usb_detection():
    """Test USB device detection for MCC devices"""
    print("\n=== USB MCC Device Detection Test ===")
    
    try:
        import usb.core
        import usb.util
        print("✓ pyusb library available")
        
        # Look specifically for MCC devices
        mcc_vendor_ids = [0x09db, 0x0683]  # MCC vendor IDs
        
        found_mcc = False
        for vendor_id in mcc_vendor_ids:
            devices = usb.core.find(find_all=True, idVendor=vendor_id)
            device_list = list(devices)
            
            if device_list:
                print(f"✓ Found {len(device_list)} MCC USB device(s) with VID {vendor_id:04x}")
                found_mcc = True
                
                for device in device_list:
                    print(f"  Device: VID:{device.idVendor:04x} PID:{device.idProduct:04x}")
                    try:
                        manufacturer = usb.util.get_string(device, device.iManufacturer)
                        product = usb.util.get_string(device, device.iProduct) 
                        print(f"    Manufacturer: {manufacturer}")
                        print(f"    Product: {product}")
                    except:
                        print("    (Could not read device strings)")
        
        if not found_mcc:
            print("✗ No MCC devices found via USB")
            print("  Check: lsusb | grep -E '09db|0683'")
        
    except ImportError:
        print("✗ pyusb not available - install with: pip3 install pyusb")
        return False
    except Exception as e:
        print(f"✗ USB detection error: {e}")
        return False
    
    return True