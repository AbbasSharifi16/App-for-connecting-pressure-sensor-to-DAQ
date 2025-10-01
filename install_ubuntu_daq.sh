#!/bin/bash

echo "Installing DAQ support for Ubuntu..."

# Update package lists
sudo apt update

# Install basic USB and serial support
echo "Installing USB and serial support..."
sudo apt install -y python3-pip python3-dev
sudo apt install -y libusb-1.0-0-dev libudev-dev
sudo apt install -y udev

# Install Python packages for DAQ support
echo "Installing Python DAQ packages..."
pip3 install --user pyusb pyserial hidapi-cffi

# Install additional USB tools for debugging
sudo apt install -y usbutils lsusb

# Set up USB permissions for non-root access
echo "Setting up USB permissions..."

# Create udev rules for common DAQ devices
sudo tee /etc/udev/rules.d/99-daq-devices.rules > /dev/null << 'EOF'
# Measurement Computing devices
SUBSYSTEM=="usb", ATTR{idVendor}=="09db", MODE="0666", GROUP="plugdev"

# National Instruments devices
SUBSYSTEM=="usb", ATTR{idVendor}=="3923", MODE="0666", GROUP="plugdev"

# Advantech devices
SUBSYSTEM=="usb", ATTR{idVendor}=="13d3", MODE="0666", GROUP="plugdev"

# Silicon Labs (common USB-serial)
SUBSYSTEM=="usb", ATTR{idVendor}=="10c4", MODE="0666", GROUP="plugdev"

# FTDI (common USB-serial)
SUBSYSTEM=="usb", ATTR{idVendor}=="0403", MODE="0666", GROUP="plugdev"

# Generic USB serial devices
SUBSYSTEM=="tty", ATTRS{idVendor}=="*", MODE="0666", GROUP="dialout"
EOF

# Add user to required groups
echo "Adding user to required groups..."
sudo usermod -a -G plugdev $USER
sudo usermod -a -G dialout $USER

# Reload udev rules
sudo udevadm control --reload-rules
sudo udevadm trigger

echo "Installation complete!"
echo "Please reboot your system or log out and back in for group changes to take effect."
echo ""
echo "After reboot, you can test device detection with:"
echo "  lsusb                    # List USB devices"
echo "  ls /dev/tty*             # List serial devices"
echo "  python3 test_daq_detection.py  # Test DAQ detection"
echo ""