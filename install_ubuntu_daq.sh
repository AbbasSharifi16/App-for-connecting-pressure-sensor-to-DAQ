#!/bin/bash

echo "Installing MCC DAQ support with uldaq for Ubuntu..."

# Update package lists
sudo apt update

# Install basic USB and serial support
echo "Installing USB and development tools..."
sudo apt install -y python3-pip python3-dev
sudo apt install -y libusb-1.0-0-dev libudev-dev
sudo apt install -y udev git cmake build-essential

# Install MCC uldaq library (C++ library first)
echo "Installing MCC uldaq C++ library..."
cd /tmp
git clone https://github.com/mccdaq/uldaq.git
cd uldaq
make
sudo make install
cd ..
rm -rf uldaq

# Install Python packages for DAQ support
echo "Installing Python DAQ packages..."
pip3 install --user uldaq pyusb pyserial hidapi-cffi

# Install additional USB tools for debugging
sudo apt install -y usbutils

# Set up USB permissions for non-root access
echo "Setting up USB permissions for MCC devices..."

# Create udev rules for MCC DAQ devices
sudo tee /etc/udev/rules.d/99-mcc-daq-devices.rules > /dev/null << 'EOF'
# Measurement Computing (MCC) devices - Primary vendor ID
SUBSYSTEM=="usb", ATTR{idVendor}=="09db", MODE="0666", GROUP="plugdev"

# Measurement Computing (MCC) devices - Alternative vendor ID  
SUBSYSTEM=="usb", ATTR{idVendor}=="0683", MODE="0666", GROUP="plugdev"

# Generic USB serial devices for MCC
SUBSYSTEM=="tty", ATTRS{idVendor}=="09db", MODE="0666", GROUP="dialout"
SUBSYSTEM=="tty", ATTRS{idVendor}=="0683", MODE="0666", GROUP="dialout"

# FTDI devices (used by some MCC devices)
SUBSYSTEM=="usb", ATTR{idVendor}=="0403", MODE="0666", GROUP="plugdev"
EOF

# Add user to required groups
echo "Adding user to required groups..."
sudo usermod -a -G plugdev $USER
sudo usermod -a -G dialout $USER

# Reload udev rules
sudo udevadm control --reload-rules
sudo udevadm trigger

echo "MCC DAQ installation complete!"
echo "Please reboot your system or log out and back in for group changes to take effect."
echo ""
echo "After reboot, you can test device detection with:"
echo "  lsusb | grep 09db           # Check for MCC devices"
echo "  python3 test_daq_detection.py  # Test DAQ detection"
echo "  python3 -c \"from uldaq import get_daq_device_inventory; print(get_daq_device_inventory())\""
echo ""