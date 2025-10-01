#!/bin/bash
# Setup script for DAQ Pressure Sensor Monitor on Ubuntu

echo "Setting up DAQ Pressure Sensor Monitor..."

# Update package list
sudo apt update

# Install Python3 and pip if not already installed
sudo apt install -y python3 python3-pip

# Install Qt5 development libraries
sudo apt install -y python3-pyqt5 python3-pyqt5-dev qttools5-dev-tools

# Install additional dependencies
sudo apt install -y python3-numpy python3-matplotlib

# Install Python packages
pip3 install -r requirements.txt

echo "Setup complete!"
echo "Run the application with: python3 daq_pressure_monitor.py"