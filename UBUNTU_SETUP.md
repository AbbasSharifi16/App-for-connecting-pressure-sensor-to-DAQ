# Ubuntu DAQ Setup Guide

This guide helps you set up DAQ device support on Ubuntu Linux.

## Quick Installation

1. **Run the installation script:**
   ```bash
   chmod +x install_ubuntu_daq.sh
   bash install_ubuntu_daq.sh
   ```

2. **Reboot your system:**
   ```bash
   sudo reboot
   ```

3. **Test device detection:**
   ```bash
   python3 test_daq_detection.py
   ```

## Manual Installation Steps

### 1. Install System Dependencies
```bash
sudo apt update
sudo apt install -y python3-pip python3-dev
sudo apt install -y libusb-1.0-0-dev libudev-dev udev
sudo apt install -y usbutils
```

### 2. Install Python Packages
```bash
pip3 install --user pyusb pyserial hidapi-cffi
pip3 install -r requirements.txt
```

### 3. Set Up USB Permissions
```bash
# Add yourself to required groups
sudo usermod -a -G plugdev $USER
sudo usermod -a -G dialout $USER

# Create udev rules for DAQ devices
sudo nano /etc/udev/rules.d/99-daq-devices.rules
```

Add this content to the udev rules file:
```
# Measurement Computing devices
SUBSYSTEM=="usb", ATTR{idVendor}=="09db", MODE="0666", GROUP="plugdev"

# National Instruments devices  
SUBSYSTEM=="usb", ATTR{idVendor}=="3923", MODE="0666", GROUP="plugdev"

# Advantech devices
SUBSYSTEM=="usb", ATTR{idVendor}=="13d3", MODE="0666", GROUP="plugdev"

# Silicon Labs (USB-serial)
SUBSYSTEM=="usb", ATTR{idVendor}=="10c4", MODE="0666", GROUP="plugdev"

# FTDI (USB-serial)
SUBSYSTEM=="usb", ATTR{idVendor}=="0403", MODE="0666", GROUP="plugdev"
```

### 4. Reload USB Rules
```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
```

### 5. Reboot
```bash
sudo reboot
```

## Testing Device Detection

### Check USB Devices
```bash
# List all USB devices
lsusb

# Check for DAQ-specific devices
lsusb | grep -E "(09db|3923|13d3|10c4|0403)"
```

### Check Serial Ports
```bash
# List serial ports
ls /dev/tty*

# Check for USB serial devices
ls /dev/ttyUSB* /dev/ttyACM*
```

### Run Python Test
```bash
python3 test_daq_detection.py
```

## Troubleshooting

### Permission Issues
If you get permission errors:
```bash
# Check your groups
groups

# You should see 'plugdev' and 'dialout'
# If not, log out and back in, or reboot
```

### Device Not Detected
1. **Check if device is connected:**
   ```bash
   dmesg | tail -20
   ```

2. **Check USB connection:**
   ```bash
   lsusb -v | grep -A 5 -B 5 "your_device_vendor"
   ```

3. **Try with sudo (for testing only):**
   ```bash
   sudo python3 test_daq_detection.py
   ```

### Common DAQ Device Vendor IDs
- **Measurement Computing**: 09db, 0683
- **National Instruments**: 3923
- **Advantech**: 13d3
- **Silicon Labs (USB-Serial)**: 10c4
- **FTDI (USB-Serial)**: 0403

## Supported DAQ Devices

The application can detect:
- **USB DAQ devices** with known vendor IDs
- **USB-to-Serial DAQ devices**
- **Generic serial DAQ devices**

For specific device communication, you may need to implement device-specific protocols in the application code.

## Need Help?

If your DAQ device isn't detected:
1. Check the manufacturer's Linux driver support
2. Look up your device's USB vendor/product ID with `lsusb`
3. Add your device's vendor ID to the application's detection list
4. Consider using device-specific Python libraries if available