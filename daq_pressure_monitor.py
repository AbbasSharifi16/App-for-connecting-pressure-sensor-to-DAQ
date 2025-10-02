#!/usr/bin/env python3
"""
DAQ Pressure Sensor Monitor
A Qt-based application for monitoring pressure sensors connected to a DAQ device.
Features:
- Visual pin layout representation
- Real-time data plotting
- Multi-channel plotting support
- Configurable pin names
- Toggle channels on/off by clicking pins
"""

import sys
import time
import random
import numpy as np
import os
import csv
import json
from ctypes import c_int, c_double, POINTER, byref
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

# DAQ-specific imports (Ubuntu/Linux only)
try:
    from uldaq import get_daq_device_inventory, DaqDevice, AiInputMode, Range, AInFlag, InterfaceType
    ULDAQ_AVAILABLE = True
except ImportError:
    ULDAQ_AVAILABLE = False

try:
    import usb.core
    import usb.util
    USB_DAQ_AVAILABLE = True
except ImportError:
    USB_DAQ_AVAILABLE = False

try:
    import serial.tools.list_ports
    SERIAL_DAQ_AVAILABLE = True
except ImportError:
    SERIAL_DAQ_AVAILABLE = False
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QGridLayout, QPushButton, QLineEdit, QLabel, QFrame, QScrollArea,
    QGroupBox, QCheckBox, QSpinBox, QComboBox, QMessageBox, QSplitter,
    QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout, QFileDialog,
    QToolButton, QMenu, QAction
)
from PyQt5.QtCore import QTimer, Qt, pyqtSignal, QThread, pyqtSlot
from PyQt5.QtGui import QPalette, QColor, QFont
import pyqtgraph as pg
from pyqtgraph import PlotWidget, mkPen

@dataclass
class CalibrationData:
    """Calibration data for a sensor"""
    point1_physical: float = 0.0  # Physical value (e.g., meters)
    point1_voltage: float = 0.0   # Corresponding voltage
    point2_physical: float = 1.0  # Physical value
    point2_voltage: float = 5.0   # Corresponding voltage
    physical_unit: str = "m"      # Unit for physical measurement
    is_calibrated: bool = False   # Whether calibration is active

@dataclass
class PinConfig:
    """Configuration for a DAQ pin"""
    pin_number: int
    name: str
    pin_type: str
    function: str
    is_analog_input: bool = False
    is_active: bool = False
    color: str = '#1f77b4'
    calibration: CalibrationData = None
    
    def __post_init__(self):
        if self.calibration is None:
            self.calibration = CalibrationData()

class StateManager:
    """Manages saving and loading application state"""
    
    def __init__(self, config_file: str = "daq_config.json"):
        self.config_file = config_file
        
    def save_state(self, pin_configs: List[PinConfig]) -> bool:
        """Save pin configurations to file"""
        try:
            state_data = {
                "version": "1.0",
                "timestamp": datetime.now().isoformat(),
                "pin_configs": []
            }
            
            for pin_config in pin_configs:
                pin_data = {
                    "pin_number": pin_config.pin_number,
                    "name": pin_config.name,
                    "pin_type": pin_config.pin_type,
                    "function": pin_config.function,
                    "is_analog_input": pin_config.is_analog_input,
                    "calibration": {
                        "point1_physical": pin_config.calibration.point1_physical,
                        "point1_voltage": pin_config.calibration.point1_voltage,
                        "point2_physical": pin_config.calibration.point2_physical,
                        "point2_voltage": pin_config.calibration.point2_voltage,
                        "physical_unit": pin_config.calibration.physical_unit,
                        "is_calibrated": pin_config.calibration.is_calibrated
                    }
                }
                state_data["pin_configs"].append(pin_data)
            
            with open(self.config_file, 'w') as f:
                json.dump(state_data, f, indent=2)
            
            print(f"State saved to {self.config_file}")
            return True
            
        except Exception as e:
            print(f"Error saving state: {e}")
            return False
    
    def load_state(self) -> Optional[List[PinConfig]]:
        """Load pin configurations from file"""
        try:
            if not os.path.exists(self.config_file):
                print(f"No config file found at {self.config_file}")
                return None
            
            with open(self.config_file, 'r') as f:
                state_data = json.load(f)
            
            pin_configs = []
            for pin_data in state_data.get("pin_configs", []):
                calibration = CalibrationData(
                    point1_physical=pin_data["calibration"]["point1_physical"],
                    point1_voltage=pin_data["calibration"]["point1_voltage"],
                    point2_physical=pin_data["calibration"]["point2_physical"],
                    point2_voltage=pin_data["calibration"]["point2_voltage"],
                    physical_unit=pin_data["calibration"]["physical_unit"],
                    is_calibrated=pin_data["calibration"]["is_calibrated"]
                )
                
                pin_config = PinConfig(
                    pin_number=pin_data["pin_number"],
                    name=pin_data["name"],
                    pin_type=pin_data["pin_type"],
                    function=pin_data["function"],
                    is_analog_input=pin_data["is_analog_input"],
                    calibration=calibration
                )
                pin_configs.append(pin_config)
            
            print(f"State loaded from {self.config_file}")
            return pin_configs
            
        except Exception as e:
            print(f"Error loading state: {e}")
            return None

class RealDAQInterface(QThread):
    """Real DAQ interface using uldaq library for MCC devices"""
    
    data_ready = pyqtSignal(int, float)  # pin_number, value
    
    def __init__(self):
        super().__init__()
        self.running = False
        self.active_pins: List[int] = []
        self.sample_rate = 100  # Hz
        self.time_offset = 0
        self.daq_type = None
        self.device = None
        self.daq_device = None  # uldaq device object
        self.detect_daq_device()
        
    def detect_daq_device(self):
        """Detect available DAQ devices using uldaq library"""
        print("Detecting MCC DAQ devices using uldaq...")
        
        # Try uldaq (MCC devices)
        if ULDAQ_AVAILABLE:
            try:
                devices = get_daq_device_inventory(InterfaceType.USB)
                if devices:
                    # Use the first available device
                    descriptor = devices[0]
                    self.daq_device = DaqDevice(descriptor)
                    
                    # Try to connect with timeout
                    print(f"Attempting to connect to: {descriptor.product_name}")
                    self.daq_device.connect()
                    
                    # Verify connection by testing device access
                    ai_device = self.daq_device.get_ai_device()
                    if not ai_device:
                        print("ERROR: Device connected but no analog input subsystem available")
                        self.daq_device.disconnect()
                        raise Exception("No analog input subsystem")
                    
                    # Test device responsiveness
                    ai_info = ai_device.get_info()
                    num_channels = ai_info.get_num_chans()
                    supported_ranges = ai_info.get_ranges(AiInputMode.SINGLE_ENDED)
                    
                    self.daq_type = "MCC_ULDAQ"
                    self.device = f"MCC {descriptor.product_name} (ID: {descriptor.product_id})"
                    print(f"Successfully connected to MCC DAQ device: {self.device}")
                    print(f"  Analog Input Channels: {num_channels}")
                    print(f"  Supported ranges: {supported_ranges}")
                    
                    # Test a quick read to verify functionality
                    try:
                        test_voltage = ai_device.a_in(0, AiInputMode.SINGLE_ENDED, Range.BIP10VOLTS, AInFlag.DEFAULT)
                        print(f"  Connection test successful - Channel 0 reading: {test_voltage:.3f}V")
                    except Exception as test_e:
                        print(f"  Warning: Connection test failed: {test_e}")
                    
                    return
                else:
                    print("No MCC DAQ devices found with uldaq")
            except Exception as e:
                print(f"uldaq detection/connection failed: {e}")
                if hasattr(self, 'daq_device') and self.daq_device:
                    try:
                        self.daq_device.disconnect()
                    except:
                        pass
                    self.daq_device = None
        
        # Try generic USB DAQ devices (fallback)
        if USB_DAQ_AVAILABLE:
            try:
                # Look for MCC vendor ID specifically
                devices = usb.core.find(find_all=True, idVendor=0x09db)  # MCC vendor ID
                for device in devices:
                    self.daq_type = "USB_MCC"
                    self.device = f"MCC USB Device (PID: {device.idProduct:04x})"
                    print(f"Found MCC USB device: {self.device}")
                    print("Note: Using generic USB - install uldaq for full functionality")
                    return
            except Exception as e:
                print(f"USB DAQ detection failed: {e}")
                
        # Try serial DAQ devices (fallback)
        if SERIAL_DAQ_AVAILABLE:
            try:
                ports = serial.tools.list_ports.comports()
                for port in ports:
                    # Look for MCC or DAQ-related keywords
                    if any(keyword in port.description.lower() for keyword in ['mcc', 'measurement computing', 'daq', 'data acquisition']):
                        self.daq_type = "SERIAL_MCC"
                        self.device = f"MCC Serial DAQ ({port.device})"
                        print(f"Found MCC Serial device: {self.device}")
                        return
            except Exception as e:
                print(f"Serial DAQ detection failed: {e}")
        
        # No real DAQ found - show error
        self.daq_type = "NONE"
        self.device = None
        print("ERROR: No MCC DAQ device detected!")
        print("Please connect an MCC DAQ device and ensure uldaq is installed:")
        print("1. Install uldaq: pip3 install uldaq")
        print("2. Install MCC drivers: https://github.com/mccdaq/uldaq")
        print("3. Check USB connections and device permissions")
        raise RuntimeError("No MCC DAQ hardware detected. Cannot proceed without real sensors.")
    
    def add_pin(self, pin_number: int):
        """Add a pin to active monitoring"""
        if pin_number not in self.active_pins:
            self.active_pins.append(pin_number)
            print(f"Added pin {pin_number} to DAQ acquisition ({self.daq_type} mode)")
            
    def remove_pin(self, pin_number: int):
        """Remove a pin from active monitoring"""
        if pin_number in self.active_pins:
            self.active_pins.remove(pin_number)
            print(f"Removed pin {pin_number} from DAQ acquisition")
            
    def start_acquisition(self):
        """Start data acquisition"""
        self.running = True
        
        if self.daq_type == "NI":
            self._setup_ni_daq()
        elif self.daq_type == "MCC":
            self._setup_mcc_daq()
        
        self.start()
        print(f"Started DAQ acquisition in {self.daq_type} mode")
        
    def _setup_ni_daq(self):
        """Setup National Instruments DAQ"""
        try:
            import nidaqmx
            from nidaqmx.constants import AcquisitionType
            
            if self.task:
                self.task.close()
            
            self.task = nidaqmx.Task()
            
            # Add analog input channels for active pins
            for pin in self.active_pins:
                channel_name = f"{self.device}/ai{pin-1}"  # Convert pin number to AI channel
                self.task.ai_channels.add_ai_voltage_chan(channel_name)
            
            print(f"NI DAQ configured for pins: {self.active_pins}")
            
        except Exception as e:
            print(f"Error setting up NI DAQ: {e}")
            self.daq_type = "SIMULATION"
    
    def _setup_mcc_daq(self):
        """Setup Measurement Computing DAQ"""
        try:
            from mcculw import ul
            from mcculw.enums import ULRange, InfoType, BoardInfo
            
            # Configure board for analog input
            ul.set_config(InfoType.BOARDINFO, self.board_num, 0, BoardInfo.ADRES, 16)
            print(f"MCC DAQ configured for pins: {self.active_pins}")
            
        except Exception as e:
            print(f"Error setting up MCC DAQ: {e}")
            self.daq_type = "SIMULATION"
        
    def stop_acquisition(self):
        """Stop data acquisition"""
        self.running = False
        
        if self.daq_type == "NI" and self.task:
            try:
                self.task.close()
                self.task = None
            except Exception as e:
                print(f"Error closing NI DAQ task: {e}")
        
        self.wait()
        print("DAQ acquisition stopped")
        
    def run(self):
        """Main acquisition loop - Real MCC sensors using uldaq"""
        if self.daq_type == "NONE":
            print("ERROR: Cannot start acquisition - no DAQ device detected!")
            return
            
        self.time_offset = time.time()
        consecutive_errors = 0
        max_consecutive_errors = 5
        
        print(f"Starting acquisition loop for {self.daq_type} device...")
        
        while self.running:
            try:
                if self.daq_type == "MCC_ULDAQ":
                    self._read_uldaq_data()
                    consecutive_errors = 0  # Reset error counter on successful read
                elif self.daq_type == "USB_MCC":
                    self._read_usb_mcc_data()
                elif self.daq_type == "SERIAL_MCC":
                    self._read_serial_mcc_data()
                else:
                    print("ERROR: Unknown DAQ type - stopping acquisition")
                    break
                    
            except Exception as e:
                consecutive_errors += 1
                print(f"Acquisition error {consecutive_errors}/{max_consecutive_errors}: {e}")
                
                if consecutive_errors >= max_consecutive_errors:
                    print("ERROR: Too many consecutive errors - stopping acquisition")
                    break
                
                # Wait a bit longer on errors
                self.msleep(1000)
                continue
                
            self.msleep(int(1000 / self.sample_rate))
            
        print("Acquisition loop ended")
    
    def _read_uldaq_data(self):
        """Read data from MCC DAQ using uldaq library"""
        try:
            if not self.daq_device:
                print("ERROR: No uldaq device available")
                return
                
            # Check if device is still connected
            try:
                # Try to access device info to verify connection
                ai_device = self.daq_device.get_ai_device()
                if not ai_device:
                    print("ERROR: No analog input device available")
                    return
                    
                # Verify device is responsive
                ai_info = ai_device.get_info()
                
            except Exception as conn_e:
                print(f"ERROR: Device connection lost: {conn_e}")
                print("Attempting to reconnect...")
                try:
                    # Try to reconnect
                    self.daq_device.connect()
                    ai_device = self.daq_device.get_ai_device()
                    if not ai_device:
                        print("ERROR: Failed to reconnect - no analog input device")
                        return
                except Exception as reconn_e:
                    print(f"ERROR: Reconnection failed: {reconn_e}")
                    return
                
            # Read from each active pin
            for pin in self.active_pins:
                try:
                    # Convert pin number to channel (MCC channels are 0-based)
                    channel = pin - 1
                    
                    # Validate channel number
                    ai_info = ai_device.get_info()
                    max_channels = ai_info.get_num_chans()
                    if channel >= max_channels:
                        print(f"ERROR: Channel {channel} (pin {pin}) exceeds device limit of {max_channels}")
                        continue
                    
                    # Read analog input - using ±10V range, single-ended mode
                    voltage = ai_device.a_in(channel, AiInputMode.SINGLE_ENDED, Range.BIP10VOLTS, AInFlag.DEFAULT)
                    
                    # Emit the voltage reading
                    self.data_ready.emit(pin, voltage)
                    
                except Exception as e:
                    print(f"Error reading channel {pin} (DAQ channel {channel}): {e}")
                    # Don't continue with other channels if there's a connection issue
                    if "connection" in str(e).lower() or "73" in str(e):
                        print("Connection error detected - stopping acquisition")
                        break
                    
        except Exception as e:
            print(f"Critical error in uldaq data acquisition: {e}")
    
    def _read_usb_mcc_data(self):
        """Read data from MCC DAQ using generic USB (limited functionality)"""
        try:
            # Generic USB implementation - limited without proper drivers
            print("WARNING: Using generic USB mode - limited functionality")
            print("Install uldaq library for full MCC device support")
            
            # For now, return zero values as placeholder
            for pin in self.active_pins:
                voltage = 0.0  # Placeholder - requires device-specific protocol
                self.data_ready.emit(pin, voltage)
                
        except Exception as e:
            print(f"Error reading USB MCC data: {e}")
    
    def _read_serial_mcc_data(self):
        """Read data from MCC DAQ using serial connection"""
        try:
            # Serial implementation for MCC devices with serial interface
            print("WARNING: Serial MCC mode - requires device-specific protocol")
            
            # For now, return zero values as placeholder  
            for pin in self.active_pins:
                voltage = 0.0  # Placeholder - requires device-specific protocol
                self.data_ready.emit(pin, voltage)
                
        except Exception as e:
            print(f"Error reading Serial MCC data: {e}")
            
    def start_acquisition(self):
        """Start data acquisition"""
        if not self.running:
            # Verify device connection before starting
            if self.daq_type == "MCC_ULDAQ" and self.daq_device:
                try:
                    # Test connection
                    ai_device = self.daq_device.get_ai_device()
                    if ai_device:
                        ai_info = ai_device.get_info()
                        print(f"Device verified: {ai_info.get_num_chans()} channels available")
                    else:
                        print("ERROR: Cannot access analog input device")
                        return
                except Exception as e:
                    print(f"ERROR: Device verification failed: {e}")
                    print("Attempting to reconnect...")
                    try:
                        self.daq_device.connect()
                        print("Reconnection successful")
                    except Exception as reconnect_e:
                        print(f"Reconnection failed: {reconnect_e}")
                        return
            
            self.running = True
            self.start()
            print(f"Started DAQ acquisition using {self.daq_type}")
    
    def stop_acquisition(self):
        """Stop data acquisition"""
        if self.running:
            self.running = False
            self.wait()  # Wait for thread to finish
            
            # Disconnect uldaq device if connected
            if self.daq_device and self.daq_type == "MCC_ULDAQ":
                try:
                    print("Disconnecting from MCC DAQ device...")
                    self.daq_device.disconnect()
                    print("Disconnected from MCC DAQ device")
                except Exception as e:
                    print(f"Warning: Error during disconnect: {e}")
                    
            print("Stopped DAQ acquisition")

# Keep DAQSimulator as an alias for backward compatibility
class DAQSimulator(RealDAQInterface):
    """Backward compatibility alias"""
    pass

class DataRecorder:
    """Class to handle CSV data recording"""
    
    def __init__(self):
        self.is_recording = False
        self.recorded_data: List[Dict] = []
        self.recording_start_time = None
        self.csv_filename = None
        
    def start_recording(self, active_pins: List[int], pin_configs: List[PinConfig]) -> str:
        """Start recording data to memory"""
        self.is_recording = True
        self.recorded_data = []
        self.recording_start_time = time.time()
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.csv_filename = f"daq_recording_{timestamp}.csv"
        
        # Create header info
        self.active_pin_configs = {pin: next(p for p in pin_configs if p.pin_number == pin) 
                                  for pin in active_pins}
        
        return self.csv_filename
    
    def add_data_point(self, pin_number: int, voltage: float, calibrated_value: float, timestamp: float):
        """Add a data point to the recording"""
        if self.is_recording:
            relative_time = timestamp - self.recording_start_time
            
            data_point = {
                'timestamp': timestamp,
                'relative_time': relative_time,
                'pin_number': pin_number,
                'voltage': voltage,
                'calibrated_value': calibrated_value
            }
            self.recorded_data.append(data_point)
    
    def stop_recording_and_save(self) -> str:
        """Stop recording and save data to CSV file"""
        if not self.is_recording:
            return None
            
        self.is_recording = False
        
        if not self.recorded_data:
            return None
        
        # Open file dialog for save location
        from PyQt5.QtWidgets import QFileDialog, QMessageBox
        
        filename, _ = QFileDialog.getSaveFileName(
            None,
            "Save Recording Data",
            self.csv_filename,
            "CSV Files (*.csv)"
        )
        
        if not filename:
            return None
            
        try:
            self.save_to_csv(filename)
            return filename
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Failed to save recording:\n{str(e)}")
            return None
    
    def save_to_csv(self, filename: str):
        """Save recorded data to CSV file"""
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            # Write header information
            csvfile.write(f"# DAQ Sensor Recording\n")
            csvfile.write(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            csvfile.write(f"# Recording Duration: {len(self.recorded_data)} data points\n")
            csvfile.write(f"# \n")
            
            # Write sensor configuration
            csvfile.write(f"# Sensor Configuration:\n")
            for pin, config in self.active_pin_configs.items():
                cal = config.calibration
                if cal.is_calibrated:
                    csvfile.write(f"# Pin {pin} ({config.name}): Calibrated to {cal.physical_unit}\n")
                    csvfile.write(f"#   Calibration: {cal.point1_physical} {cal.physical_unit} @ {cal.point1_voltage} V, ")
                    csvfile.write(f"{cal.point2_physical} {cal.physical_unit} @ {cal.point2_voltage} V\n")
                else:
                    csvfile.write(f"# Pin {pin} ({config.name}): Raw voltage (not calibrated)\n")
            csvfile.write(f"# \n")
            
            # Create column headers
            headers = ['Timestamp (Unix)', 'Relative Time (s)', 'Pin Number', 'Sensor Name', 'Voltage (V)']
            
            # Add calibrated value columns for each unique unit
            units = set()
            for config in self.active_pin_configs.values():
                if config.calibration.is_calibrated:
                    units.add(config.calibration.physical_unit)
            
            for unit in sorted(units):
                headers.append(f'Calibrated Value ({unit})')
            
            if not units:  # No calibrated sensors
                headers.append('Calibrated Value')
            
            writer = csv.writer(csvfile)
            writer.writerow(headers)
            
            # Write data points
            for data_point in self.recorded_data:
                pin_config = self.active_pin_configs[data_point['pin_number']]
                
                row = [
                    f"{data_point['timestamp']:.6f}",
                    f"{data_point['relative_time']:.3f}",
                    data_point['pin_number'],
                    pin_config.name,
                    f"{data_point['voltage']:.6f}"
                ]
                
                # Add calibrated values
                if pin_config.calibration.is_calibrated:
                    cal_unit = pin_config.calibration.physical_unit
                    for unit in sorted(units):
                        if unit == cal_unit:
                            row.append(f"{data_point['calibrated_value']:.6f}")
                        else:
                            row.append('')  # Empty for other units
                else:
                    if units:
                        row.extend([''] * len(units))
                    else:
                        row.append(f"{data_point['voltage']:.6f}")  # Use voltage if no calibration
                
                writer.writerow(row)

class CalibrationDialog(QDialog):
    """Dialog for sensor calibration"""
    
    def __init__(self, pin_config: PinConfig, parent=None):
        super().__init__(parent)
        self.pin_config = pin_config
        self.setup_ui()
        self.load_current_values()
        
    def setup_ui(self):
        """Setup the calibration dialog UI"""
        self.setWindowTitle(f"Calibrate {self.pin_config.name} (Pin {self.pin_config.pin_number})")
        self.setModal(True)
        self.resize(500, 400)
        self.setMinimumSize(450, 350)
        
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel(f"Linear Calibration for {self.pin_config.name}")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setStyleSheet("color: #333; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Instructions
        instructions = QLabel(
            "Enter two calibration points to establish a linear relationship\n"
            "between voltage readings and physical measurements."
        )
        instructions.setWordWrap(True)
        instructions.setFont(QFont("Arial", 10))
        instructions.setStyleSheet("color: #666; margin-bottom: 15px;")
        layout.addWidget(instructions)
        
        # Calibration form
        form_layout = QFormLayout()
        
        # Physical unit
        self.unit_edit = QLineEdit()
        self.unit_edit.setPlaceholderText("e.g., m, psi, Pa, etc.")
        self.unit_edit.setMinimumHeight(30)
        self.unit_edit.setFont(QFont("Arial", 10))
        form_layout.addRow("Physical Unit:", self.unit_edit)
        
        # First calibration point
        point1_group = QGroupBox("Calibration Point 1")
        point1_group.setFont(QFont("Arial", 10, QFont.Bold))
        point1_layout = QHBoxLayout(point1_group)
        point1_layout.setSpacing(10)
        
        self.point1_physical = QDoubleSpinBox()
        self.point1_physical.setDecimals(3)
        self.point1_physical.setRange(-999999, 999999)
        self.point1_physical.setSuffix(" (physical)")
        self.point1_physical.setMinimumHeight(30)
        self.point1_physical.setFont(QFont("Arial", 10))
        
        point1_layout.addWidget(QLabel("Physical Value:"))
        point1_layout.addWidget(self.point1_physical)
        
        point1_layout.addWidget(QLabel("~"))
        
        self.point1_voltage = QDoubleSpinBox()
        self.point1_voltage.setDecimals(3)
        self.point1_voltage.setRange(-999999, 999999)
        self.point1_voltage.setSuffix(" V")
        self.point1_voltage.setMinimumHeight(30)
        self.point1_voltage.setFont(QFont("Arial", 10))
        
        point1_layout.addWidget(QLabel("Voltage:"))
        point1_layout.addWidget(self.point1_voltage)
        
        layout.addWidget(point1_group)
        
        # Second calibration point
        point2_group = QGroupBox("Calibration Point 2")
        point2_group.setFont(QFont("Arial", 10, QFont.Bold))
        point2_layout = QHBoxLayout(point2_group)
        point2_layout.setSpacing(10)
        
        self.point2_physical = QDoubleSpinBox()
        self.point2_physical.setDecimals(3)
        self.point2_physical.setRange(-999999, 999999)
        self.point2_physical.setSuffix(" (physical)")
        self.point2_physical.setMinimumHeight(30)
        self.point2_physical.setFont(QFont("Arial", 10))
        
        point2_layout.addWidget(QLabel("Physical Value:"))
        point2_layout.addWidget(self.point2_physical)
        
        point2_layout.addWidget(QLabel("~"))
        
        self.point2_voltage = QDoubleSpinBox()
        self.point2_voltage.setDecimals(3)
        self.point2_voltage.setRange(-999999, 999999)
        self.point2_voltage.setSuffix(" V")
        self.point2_voltage.setMinimumHeight(30)
        self.point2_voltage.setFont(QFont("Arial", 10))
        
        point2_layout.addWidget(QLabel("Voltage:"))
        point2_layout.addWidget(self.point2_voltage)
        
        layout.addWidget(point2_group)
        
        # Enable calibration checkbox
        self.enable_calibration = QCheckBox("Enable Calibration")
        self.enable_calibration.setFont(QFont("Arial", 10, QFont.Bold))
        self.enable_calibration.setStyleSheet("color: #333; margin: 10px 0;")
        layout.addWidget(self.enable_calibration)
        
        # Preview of calibration equation
        equation_title = QLabel("Calibration Equation Preview:")
        equation_title.setFont(QFont("Arial", 10, QFont.Bold))
        equation_title.setStyleSheet("color: #333; margin-top: 10px;")
        layout.addWidget(equation_title)
        
        self.equation_label = QLabel()
        self.equation_label.setStyleSheet("""
            QLabel {
                font-family: 'Courier New', monospace;
                background-color: #f8f8f8;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 10px;
                margin: 5px 0;
                font-size: 10px;
                line-height: 1.4;
            }
        """)
        self.equation_label.setWordWrap(True)
        self.equation_label.setMinimumHeight(60)
        layout.addWidget(self.equation_label)
        
        # Connect signals for real-time preview
        self.point1_physical.valueChanged.connect(self.update_equation_preview)
        self.point1_voltage.valueChanged.connect(self.update_equation_preview)
        self.point2_physical.valueChanged.connect(self.update_equation_preview)
        self.point2_voltage.valueChanged.connect(self.update_equation_preview)
        self.unit_edit.textChanged.connect(self.update_equation_preview)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # Initial equation preview
        self.update_equation_preview()
        
    def load_current_values(self):
        """Load current calibration values into the dialog"""
        cal = self.pin_config.calibration
        self.point1_physical.setValue(cal.point1_physical)
        self.point1_voltage.setValue(cal.point1_voltage)
        self.point2_physical.setValue(cal.point2_physical)
        self.point2_voltage.setValue(cal.point2_voltage)
        self.unit_edit.setText(cal.physical_unit)
        self.enable_calibration.setChecked(cal.is_calibrated)
        
    def update_equation_preview(self):
        """Update the calibration equation preview"""
        try:
            p1_phys = self.point1_physical.value()
            p1_volt = self.point1_voltage.value()
            p2_phys = self.point2_physical.value()
            p2_volt = self.point2_voltage.value()
            unit = self.unit_edit.text() or "units"
            
            if abs(p2_volt - p1_volt) < 1e-6:
                self.equation_label.setText("Error: Voltage values must be different!")
                return
                
            # Calculate linear calibration: physical = m * voltage + b
            slope = (p2_phys - p1_phys) / (p2_volt - p1_volt)
            intercept = p1_phys - slope * p1_volt
            
            equation = f"Physical = {slope:.6f} × Voltage + {intercept:.6f}\n"
            equation += f"Units: {unit}\n"
            equation += f"Range: {min(p1_phys, p2_phys):.3f} to {max(p1_phys, p2_phys):.3f} {unit}"
            
            self.equation_label.setText(equation)
            
        except Exception as e:
            self.equation_label.setText(f"Error in calculation: {str(e)}")
            
    def get_calibration_data(self) -> CalibrationData:
        """Get the calibration data from the dialog"""
        return CalibrationData(
            point1_physical=self.point1_physical.value(),
            point1_voltage=self.point1_voltage.value(),
            point2_physical=self.point2_physical.value(),
            point2_voltage=self.point2_voltage.value(),
            physical_unit=self.unit_edit.text() or "units",
            is_calibrated=self.enable_calibration.isChecked()
        )

class PinButton(QCheckBox):
    """Custom checkbox representing a DAQ pin"""
    
    def __init__(self, pin_config: PinConfig):
        super().__init__()
        self.pin_config = pin_config
        self.is_monitoring = False
        self.setup_button()
        
    def setup_button(self):
        """Setup button appearance and properties"""
        self.setText(f"Pin {self.pin_config.pin_number}\n{self.pin_config.name}")
        self.setFixedSize(100, 70)  # Increased size
        self.setFont(QFont("Arial", 9, QFont.Bold))
        
        if self.pin_config.is_analog_input:
            self.setStyleSheet("""
                QCheckBox {
                    background-color: transparent;
                    border: none;
                    font-weight: bold;
                    font-size: 9px;
                    color: #2196F3;
                    spacing: 10px;
                }
                QCheckBox:hover {
                    color: #1976D2;
                }
                QCheckBox::indicator {
                    width: 18px;
                    height: 18px;
                    border: 2px solid #2196F3;
                    background-color: white;
                    border-radius: 3px;
                }
                QCheckBox::indicator:checked {
                    background-color: #2196F3;
                    border: 2px solid #1976D2;
                }
                QCheckBox::indicator:hover {
                    border: 2px solid #1976D2;
                }
            """)
        else:
            self.setStyleSheet("""
                QCheckBox {
                    background-color: transparent;
                    border: none;
                    font-size: 8px;
                    color: #999;
                    spacing: 10px;
                }
                QCheckBox:disabled {
                    color: #ccc;
                }
                QCheckBox::indicator {
                    width: 14px;
                    height: 14px;
                    border: 2px solid #ccc;
                    background-color: #f5f5f5;
                    border-radius: 3px;
                }
                QCheckBox::indicator:disabled {
                    background-color: #eeeeee;
                    border: 2px solid #ddd;
                }
            """)
            self.setEnabled(False)
            
    def set_monitoring(self, monitoring: bool):
        """Update button appearance based on monitoring status"""
        self.is_monitoring = monitoring
        if self.pin_config.is_analog_input:
            if monitoring:
                self.setStyleSheet("""
                    QCheckBox {
                        background-color: transparent;
                        border: none;
                        font-weight: bold;
                        font-size: 9px;
                        color: #4CAF50;
                        spacing: 10px;
                    }
                    QCheckBox:hover {
                        color: #388E3C;
                    }
                    QCheckBox::indicator {
                        width: 18px;
                        height: 18px;
                        border: 2px solid #4CAF50;
                        background-color: white;
                        border-radius: 3px;
                    }
                    QCheckBox::indicator:checked {
                        background-color: #4CAF50;
                        border: 2px solid #388E3C;
                    }
                    QCheckBox::indicator:hover {
                        border: 2px solid #388E3C;
                    }
                """)
            else:
                self.setup_button()

class PinNameEditor(QWidget):
    """Widget for editing pin names"""
    
    def __init__(self, pin_configs: List[PinConfig], pin_buttons: Dict[int, 'PinButton'] = None):
        super().__init__()
        self.pin_configs = pin_configs
        self.pin_buttons = pin_buttons  # Reference to pin buttons to update text
        self.name_editors: Dict[int, QLineEdit] = {}
        self.calibration_buttons: Dict[int, QPushButton] = {}
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the pin name editor UI"""
        layout = QVBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Title
        title = QLabel("Pin Configuration")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        title.setStyleSheet("color: #333; margin-bottom: 5px;")
        layout.addWidget(title)
        
        # Scroll area for pin editors
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setMinimumHeight(250)
        scroll.setMaximumHeight(350)
        
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(5)
        
        for pin_config in self.pin_configs:
            if pin_config.is_analog_input:
                pin_frame = QFrame()
                pin_frame.setFrameStyle(QFrame.Box)
                pin_frame.setStyleSheet("""
                    QFrame {
                        border: 1px solid #ddd;
                        border-radius: 4px;
                        background-color: #fafafa;
                        margin: 2px;
                        padding: 4px;
                    }
                """)
                pin_layout = QHBoxLayout(pin_frame)
                pin_layout.setContentsMargins(8, 6, 8, 6)
                pin_layout.setSpacing(8)
                
                # Pin number label
                pin_label = QLabel(f"Pin {pin_config.pin_number}:")
                pin_label.setFixedWidth(70)
                pin_label.setFont(QFont("Arial", 10, QFont.Bold))
                pin_label.setStyleSheet("color: #555;")
                
                # Name editor
                name_editor = QLineEdit(pin_config.name)
                name_editor.setMinimumHeight(25)
                name_editor.setFont(QFont("Arial", 10))
                name_editor.setStyleSheet("""
                    QLineEdit {
                        border: 1px solid #ccc;
                        border-radius: 3px;
                        padding: 4px;
                        background-color: white;
                    }
                    QLineEdit:focus {
                        border: 2px solid #2196F3;
                    }
                """)
                name_editor.textChanged.connect(
                    lambda text, pin=pin_config.pin_number: self.update_pin_name(pin, text)
                )
                self.name_editors[pin_config.pin_number] = name_editor
                
                # Calibration button
                cal_button = QPushButton("Cal")
                cal_button.setFixedSize(50, 25)
                cal_button.setFont(QFont("Arial", 9, QFont.Bold))
                cal_button.setToolTip(f"Calibrate sensor on pin {pin_config.pin_number}")
                cal_button.clicked.connect(
                    lambda checked, pin=pin_config.pin_number: self.open_calibration_dialog(pin)
                )
                self.calibration_buttons[pin_config.pin_number] = cal_button
                
                # Update button style based on calibration status
                self.update_calibration_button_style(pin_config.pin_number)
                
                pin_layout.addWidget(pin_label)
                pin_layout.addWidget(name_editor)
                pin_layout.addWidget(cal_button)
                scroll_layout.addWidget(pin_frame)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)
        
        self.setLayout(layout)
        
    def update_pin_name(self, pin_number: int, name: str):
        """Update pin name in configuration"""
        for pin_config in self.pin_configs:
            if pin_config.pin_number == pin_number:
                pin_config.name = name
                # Update the radio button text if buttons are available
                if self.pin_buttons and pin_number in self.pin_buttons:
                    button = self.pin_buttons[pin_number]
                    button.setText(f"Pin {pin_config.pin_number}\n{pin_config.name}")
                # Save state after name update
                if hasattr(self.parent(), 'save_state'):
                    self.parent().save_state()
                break
                
    def open_calibration_dialog(self, pin_number: int):
        """Open calibration dialog for a specific pin"""
        pin_config = next((p for p in self.pin_configs if p.pin_number == pin_number), None)
        if pin_config:
            dialog = CalibrationDialog(pin_config, self)
            if dialog.exec_() == QDialog.Accepted:
                pin_config.calibration = dialog.get_calibration_data()
                self.update_calibration_button_style(pin_number)
                # Save state after calibration update
                if hasattr(self.parent(), 'save_state'):
                    self.parent().save_state()
                
    def update_calibration_button_style(self, pin_number: int):
        """Update calibration button style based on calibration status"""
        pin_config = next((p for p in self.pin_configs if p.pin_number == pin_number), None)
        button = self.calibration_buttons.get(pin_number)
        
        if pin_config and button:
            if pin_config.calibration.is_calibrated:
                button.setStyleSheet("""
                    QPushButton {
                        background-color: #4CAF50;
                        color: white;
                        border: 1px solid #388E3C;
                        border-radius: 3px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: #66BB6A;
                    }
                """)
                button.setToolTip(f"Calibrated: {pin_config.calibration.physical_unit}")
            else:
                button.setStyleSheet("""
                    QPushButton {
                        background-color: #f0f0f0;
                        color: #333;
                        border: 1px solid #ccc;
                        border-radius: 3px;
                    }
                    QPushButton:hover {
                        background-color: #e0e0e0;
                    }
                """)
                button.setToolTip(f"Click to calibrate pin {pin_number}")

    @staticmethod
    def apply_calibration(voltage: float, calibration: CalibrationData) -> float:
        """Apply linear calibration to convert voltage to physical units"""
        if not calibration.is_calibrated:
            return voltage
            
        # Linear interpolation: physical = m * voltage + b
        voltage_diff = calibration.point2_voltage - calibration.point1_voltage
        
        if abs(voltage_diff) < 1e-6:  # Avoid division by zero
            return calibration.point1_physical
            
        slope = (calibration.point2_physical - calibration.point1_physical) / voltage_diff
        intercept = calibration.point1_physical - slope * calibration.point1_voltage
        
        return slope * voltage + intercept

class PlotWidget(QWidget):
    """Main plotting widget with real-time capabilities"""
    
    def __init__(self):
        super().__init__()
        self.plot_data: Dict[int, Dict] = {}  # pin_number -> {x_data, y_data, curve}
        self.colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', 
                      '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
        self.color_index = 0
        self.max_points = 1000  # Maximum points to keep in memory
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the plotting UI"""
        layout = QVBoxLayout()
        
        # Control buttons for the plot
        control_layout = QHBoxLayout()
        
        # Save button with dropdown menu
        self.save_button = QToolButton()
        self.save_button.setText("Save Plot")
        self.save_button.setPopupMode(QToolButton.MenuButtonPopup)
        
        # Create save menu
        save_menu = QMenu(self.save_button)
        
        save_pdf_action = QAction("Save as PDF", self)
        save_pdf_action.triggered.connect(self.save_as_pdf)
        save_menu.addAction(save_pdf_action)
        
        save_jpg_action = QAction("Save as JPG", self)
        save_jpg_action.triggered.connect(self.save_as_jpg)
        save_menu.addAction(save_jpg_action)
        
        save_png_action = QAction("Save as PNG", self)
        save_png_action.triggered.connect(self.save_as_png)
        save_menu.addAction(save_png_action)
        
        self.save_button.setMenu(save_menu)
        self.save_button.setDefaultAction(save_pdf_action)  # Default to PDF
        
        # Style the save button
        self.save_button.setStyleSheet("""
            QToolButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 12px;
                min-width: 100px;
                min-height: 35px;
            }
            QToolButton:hover {
                background-color: #1976D2;
            }
            QToolButton::menu-button {
                border: none;
                width: 20px;
            }
        """)
        
        control_layout.addWidget(self.save_button)
        control_layout.addStretch()  # Push button to the left
        
        layout.addLayout(control_layout)
        
        # Plot widget
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setLabel('left', 'Value')
        self.plot_widget.setLabel('bottom', 'Time (seconds)')
        self.plot_widget.setTitle('Real-time Sensor Data')
        self.plot_widget.showGrid(x=True, y=True)
        self.plot_widget.addLegend()
        
        layout.addWidget(self.plot_widget)
        self.setLayout(layout)
        
    def add_channel(self, pin_number: int, pin_name: str, pin_config: PinConfig) -> str:
        """Add a new channel to the plot"""
        if pin_number not in self.plot_data:
            color = self.colors[self.color_index % len(self.colors)]
            self.color_index += 1
            
            # Determine units for display
            if pin_config.calibration.is_calibrated:
                units = pin_config.calibration.physical_unit
                label_name = f"Pin {pin_number}: {pin_name} ({units})"
            else:
                units = "V"
                label_name = f"Pin {pin_number}: {pin_name} (V)"
            
            # Create curve
            pen = mkPen(color=color, width=2)
            curve = self.plot_widget.plot([], [], pen=pen, name=label_name)
            
            self.plot_data[pin_number] = {
                'x_data': [],
                'y_data': [],
                'curve': curve,
                'color': color,
                'start_time': time.time(),
                'pin_config': pin_config
            }
            
            # Update plot labels based on active channels
            self.update_plot_labels()
            
            return color
        return self.plot_data[pin_number]['color']
        
    def remove_channel(self, pin_number: int):
        """Remove a channel from the plot"""
        if pin_number in self.plot_data:
            self.plot_widget.removeItem(self.plot_data[pin_number]['curve'])
            del self.plot_data[pin_number]
            self.update_plot_labels()
            
    def update_plot_labels(self):
        """Update plot axis labels based on active channels"""
        if not self.plot_data:
            self.plot_widget.setLabel('left', 'Value')
            return
            
        # Check if all channels use the same units
        units = set()
        for data in self.plot_data.values():
            pin_config = data['pin_config']
            if pin_config.calibration.is_calibrated:
                units.add(pin_config.calibration.physical_unit)
            else:
                units.add('V')
                
        if len(units) == 1:
            unit = list(units)[0]
            self.plot_widget.setLabel('left', f'Value ({unit})')
        else:
            self.plot_widget.setLabel('left', 'Value (Mixed Units)')
            
    def update_data(self, pin_number: int, voltage: float, pin_config: PinConfig):
        """Update data for a specific channel"""
        if pin_number in self.plot_data:
            current_time = time.time() - self.plot_data[pin_number]['start_time']
            
            # Apply calibration if enabled
            if pin_config.calibration.is_calibrated:
                display_value = PinNameEditor.apply_calibration(voltage, pin_config.calibration)
            else:
                display_value = voltage
            
            # Add new data point
            self.plot_data[pin_number]['x_data'].append(current_time)
            self.plot_data[pin_number]['y_data'].append(display_value)
            
            # Limit data points to prevent memory issues
            if len(self.plot_data[pin_number]['x_data']) > self.max_points:
                self.plot_data[pin_number]['x_data'].pop(0)
                self.plot_data[pin_number]['y_data'].pop(0)
                
            # Update the curve
            self.plot_data[pin_number]['curve'].setData(
                self.plot_data[pin_number]['x_data'],
                self.plot_data[pin_number]['y_data']
            )
    
    def save_as_pdf(self):
        """Save the plot as PDF"""
        self.save_plot('PDF Files (*.pdf)', '.pdf')
    
    def save_as_jpg(self):
        """Save the plot as JPG"""
        self.save_plot('JPEG Files (*.jpg)', '.jpg')
    
    def save_as_png(self):
        """Save the plot as PNG"""
        self.save_plot('PNG Files (*.png)', '.png')
    
    def save_plot(self, file_filter: str, extension: str):
        """Generic method to save plot in different formats"""
        if not self.plot_data:
            QMessageBox.warning(self, "No Data", "No data to save. Please start monitoring and select channels first.")
            return
        
        # Generate default filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"daq_plot_{timestamp}{extension}"
        
        # Open file dialog
        filename, _ = QFileDialog.getSaveFileName(
            self,
            f"Save Plot as {extension.upper()}",
            default_filename,
            file_filter
        )
        
        if filename:
            try:
                if extension.lower() == '.pdf':
                    self.export_pdf(filename)
                else:
                    self.export_image(filename)
                    
                QMessageBox.information(self, "Success", f"Plot saved successfully as:\n{filename}")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save plot:\n{str(e)}")
    
    def export_pdf(self, filename: str):
        """Export plot as PDF using matplotlib"""
        try:
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_pdf import PdfPages
            
            # Create matplotlib figure
            fig, ax = plt.subplots(figsize=(12, 8))
            
            # Plot each channel
            for pin_number, data in self.plot_data.items():
                pin_config = data['pin_config']
                if pin_config.calibration.is_calibrated:
                    units = pin_config.calibration.physical_unit
                    label = f"Pin {pin_number}: {pin_config.name} ({units})"
                else:
                    label = f"Pin {pin_number}: {pin_config.name} (V)"
                
                ax.plot(data['x_data'], data['y_data'], 
                       color=data['color'], linewidth=2, label=label)
            
            # Customize plot
            ax.set_xlabel('Time (seconds)')
            ax.set_ylabel(self.get_y_label())
            ax.set_title('DAQ Sensor Data Export')
            ax.grid(True, alpha=0.3)
            ax.legend()
            
            # Add timestamp and info
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            fig.suptitle(f'DAQ Sensor Monitor - Exported on {timestamp}', fontsize=10, y=0.02)
            
            # Save to PDF
            with PdfPages(filename) as pdf:
                pdf.savefig(fig, bbox_inches='tight', dpi=300)
            
            plt.close(fig)
            
        except ImportError:
            # Fallback to pyqtgraph export if matplotlib not available
            self.export_image(filename.replace('.pdf', '.png'))
            QMessageBox.warning(self, "Warning", 
                              "Matplotlib not available. Saved as PNG instead.\n"
                              "Install matplotlib for PDF export: pip install matplotlib")
    
    def export_image(self, filename: str):
        """Export plot as image (PNG/JPG) using pyqtgraph"""
        # Get the plot widget's view box
        exporter = pg.exporters.ImageExporter(self.plot_widget.plotItem)
        
        # Set high resolution
        exporter.parameters()['width'] = 1920
        exporter.parameters()['height'] = 1080
        
        # Export the image
        exporter.export(filename)
    
    def get_y_label(self) -> str:
        """Get appropriate Y-axis label based on active channels"""
        if not self.plot_data:
            return 'Value'
            
        # Check if all channels use the same units
        units = set()
        for data in self.plot_data.values():
            pin_config = data['pin_config']
            if pin_config.calibration.is_calibrated:
                units.add(pin_config.calibration.physical_unit)
            else:
                units.add('V')
                
        if len(units) == 1:
            unit = list(units)[0]
            return f'Value ({unit})'
        else:
            return 'Value (Mixed Units)'

class DAQMonitorApp(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.state_manager = StateManager()
        self.pin_configs = self.load_or_create_pin_configs()
        self.pin_buttons: Dict[int, PinButton] = {}
        
        # Initialize DAQ interface - must have real hardware
        try:
            self.daq_simulator = DAQSimulator()
            if self.daq_simulator.daq_type == "NONE":
                self.show_daq_error_and_exit()
                return
        except RuntimeError as e:
            self.show_daq_error_and_exit(str(e))
            return
            
        self.data_recorder = DataRecorder()
        self.setup_ui()
        self.setup_connections()
        
    def show_daq_error_and_exit(self, error_msg: str = None):
        """Show DAQ error message and exit application"""
        from PyQt5.QtWidgets import QMessageBox
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle("DAQ Hardware Required")
        msg.setText("No DAQ hardware detected!")
        
        details = error_msg or "This application requires a real DAQ device to function.\n\n"
        details += "Please ensure:\n"
        details += "• DAQ device is connected via USB\n"
        details += "• Device drivers are installed\n"
        details += "• Device has proper permissions\n"
        details += "• Required Python packages are installed:\n"
        details += "  - pip install pyusb\n"
        details += "  - pip install pyserial\n\n"
        details += "Supported devices:\n"
        details += "• Measurement Computing DAQ devices\n"
        details += "• National Instruments DAQ devices\n"
        details += "• Advantech DAQ devices\n"
        details += "• Generic USB/Serial DAQ devices"
        
        msg.setDetailedText(details)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()
        
        # Exit the application
        import sys
        sys.exit(1)
        
    def load_or_create_pin_configs(self) -> List[PinConfig]:
        """Load pin configurations from file or create defaults"""
        # Try to load saved state first
        loaded_configs = self.state_manager.load_state()
        if loaded_configs:
            return loaded_configs
        
        # If no saved state, create default configurations
        return self.create_pin_configs()
        
    def create_pin_configs(self) -> List[PinConfig]:
        """Create pin configurations based on DAQ specifications"""
        configs = []
        
        # Single-ended analog inputs (pins 1, 2, 4, 5, 7, 8, 10, 11)
        analog_pins = [1, 2, 4, 5, 7, 8, 10, 11]
        for i, pin in enumerate(analog_pins):
            configs.append(PinConfig(
                pin_number=pin,
                name=f"Pressure_{i+1}",
                pin_type="Analog Input",
                function=f"CH{i} IN",
                is_analog_input=True
            ))
            
        # Ground pins
        ground_pins = [3, 6, 9, 12, 15, 17, 29, 31, 40]
        for pin in ground_pins:
            configs.append(PinConfig(
                pin_number=pin,
                name="GND",
                pin_type="Ground",
                function="Ground",
                is_analog_input=False
            ))
            
        # Analog outputs
        configs.extend([
            PinConfig(13, "AO0", "Analog Output", "D/A OUT 0"),
            PinConfig(14, "AO1", "Analog Output", "D/A OUT 1")
        ])
        
        # Digital and control pins
        configs.extend([
            PinConfig(16, "Reserved", "Reserved", "Reserved"),
            PinConfig(18, "Trigger", "Digital Input", "TRIG_IN"),
            PinConfig(19, "Sync", "Digital I/O", "SYNC"),
            PinConfig(20, "Counter", "Digital Input", "CTR"),
            PinConfig(30, "Power", "Power Output", "+VO")
        ])
        
        # Digital I/O ports A and B
        for i in range(8):
            configs.append(PinConfig(21+i, f"PA{i}", "Digital I/O", f"Port A{i}"))
            configs.append(PinConfig(32+i, f"PB{i}", "Digital I/O", f"Port B{i}"))
            
        return sorted(configs, key=lambda x: x.pin_number)
        
    def setup_ui(self):
        """Setup the main user interface"""
        self.setWindowTitle("DAQ Pressure Sensor Monitor")
        self.setGeometry(100, 100, 1600, 900)
        self.setMinimumSize(1200, 700)  # Allow window to be resized but set minimum size
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        
        # Top control bar
        top_control_bar = self.create_top_control_bar()
        main_layout.addWidget(top_control_bar)
        
        # Main splitter
        main_splitter = QSplitter(Qt.Horizontal)
        
        # Left panel
        left_panel = self.create_left_panel()
        main_splitter.addWidget(left_panel)
        
        # Right panel (plot)
        self.plot_widget = PlotWidget()
        main_splitter.addWidget(self.plot_widget)
        
        # Set splitter proportions
        main_splitter.setSizes([500, 1100])  # Give more space to the plot
        
        main_layout.addWidget(main_splitter)
        
    def create_top_control_bar(self) -> QWidget:
        """Create the top control bar with recording controls"""
        control_bar = QFrame()
        control_bar.setFrameStyle(QFrame.StyledPanel)
        control_bar.setMaximumHeight(100)
        control_bar.setMinimumHeight(90)
        
        layout = QHBoxLayout(control_bar)
        layout.setSpacing(15)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Recording controls
        recording_group = QGroupBox("Data Recording")
        recording_group.setFont(QFont("Arial", 10, QFont.Bold))
        recording_layout = QHBoxLayout(recording_group)
        
        self.record_button = QPushButton("Start Recording")
        self.record_button.setFixedSize(140, 40)
        self.record_button.clicked.connect(self.toggle_recording)
        self.record_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        
        # Save state button
        self.save_button = QPushButton("Save Settings")
        self.save_button.setFixedSize(140, 40)
        self.save_button.clicked.connect(self.save_state)
        self.save_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        
        self.recording_status = QLabel("Ready to record")
        self.recording_status.setStyleSheet("color: #666; font-style: italic; font-size: 12px;")
        self.recording_status.setWordWrap(True)
        
        recording_layout.addWidget(self.record_button)
        recording_layout.addWidget(self.save_button)
        recording_layout.addWidget(self.recording_status)
        recording_layout.addStretch()
        
        layout.addWidget(recording_group)
        
        # Monitoring controls
        monitoring_group = QGroupBox("System Controls")
        monitoring_group.setFont(QFont("Arial", 10, QFont.Bold))
        monitoring_layout = QHBoxLayout(monitoring_group)
        
        self.start_button = QPushButton("Start Monitoring")
        self.start_button.clicked.connect(self.start_monitoring)
        self.start_button.setFixedSize(140, 40)
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        
        self.stop_button = QPushButton("Stop Monitoring")
        self.stop_button.clicked.connect(self.stop_monitoring)
        self.stop_button.setEnabled(False)
        self.stop_button.setFixedSize(140, 40)
        self.stop_button.setStyleSheet("""
            QPushButton {
                background-color: #ff9800;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #e68900;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        
        monitoring_layout.addWidget(self.start_button)
        monitoring_layout.addWidget(self.stop_button)
        
        # DAQ device status
        self.daq_status = QLabel()
        self.daq_status.setStyleSheet("color: #333; font-weight: bold; font-size: 12px;")
        self.update_daq_status_display()
        monitoring_layout.addWidget(self.daq_status)
        monitoring_layout.addStretch()
        
        layout.addWidget(monitoring_group)
        layout.addStretch()
        
        return control_bar
        
    def create_left_panel(self) -> QWidget:
        """Create the left panel with pin layout and controls"""
        panel = QWidget()
        panel.setMinimumWidth(450)
        panel.setMaximumWidth(550)
        layout = QVBoxLayout(panel)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Pin name editor
        self.pin_editor = PinNameEditor(self.pin_configs)
        layout.addWidget(self.pin_editor)
        
        # Pin layout with scroll area
        pin_group = QGroupBox("DAQ Pin Layout (40-pin connector)")
        pin_group.setFont(QFont("Arial", 11, QFont.Bold))
        pin_group_layout = QVBoxLayout(pin_group)
        
        # Create scroll area for pin layout
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setMinimumHeight(100)
        
        # Pin container widget
        pin_container = QWidget()
        pin_layout = QGridLayout(pin_container)
        pin_layout.setSpacing(10)
        pin_layout.setContentsMargins(10, 10, 10, 10)
        
        # Create pin buttons in two columns (representing physical layout)
        for i, pin_config in enumerate(self.pin_configs):
            button = PinButton(pin_config)
            button.toggled.connect(lambda checked, pin=pin_config.pin_number: self.toggle_pin(pin, checked))
            self.pin_buttons[pin_config.pin_number] = button
            
            # Arrange in two columns
            row = (pin_config.pin_number - 1) // 2
            col = (pin_config.pin_number - 1) % 2
            pin_layout.addWidget(button, row, col)
        
        # Set container size to accommodate all pins
        pin_container.setMinimumSize(400, 20 * 35)  # 20 rows × 35px height per row
        
        # Now that pin buttons are created, pass reference to pin editor
        self.pin_editor.pin_buttons = self.pin_buttons
        
        scroll_area.setWidget(pin_container)
        pin_group_layout.addWidget(scroll_area)
        
        layout.addWidget(pin_group)
        layout.addStretch()  # Push everything to the top
        
        return panel
        
    def setup_connections(self):
        """Setup signal connections"""
        self.daq_simulator.data_ready.connect(self.update_plot_data)
        
    def toggle_pin(self, pin_number: int, checked: bool):
        """Toggle monitoring for a specific pin"""
        button = self.pin_buttons[pin_number]
        pin_config = next(p for p in self.pin_configs if p.pin_number == pin_number)
        
        if not pin_config.is_analog_input:
            button.setChecked(False)  # Uncheck if not analog input
            return
            
        if checked:
            # Start monitoring this pin
            button.set_monitoring(True)
            color = self.plot_widget.add_channel(pin_number, pin_config.name, pin_config)
            pin_config.color = color
            self.daq_simulator.add_pin(pin_number)
        else:
            # Stop monitoring this pin
            button.set_monitoring(False)
            self.daq_simulator.remove_pin(pin_number)
            self.plot_widget.remove_channel(pin_number)
            
    def toggle_recording(self):
        """Toggle data recording on/off"""
        if not self.data_recorder.is_recording:
            self.start_recording()
        else:
            self.stop_recording()
    
    def start_recording(self):
        """Start recording data from active sensors"""
        # Get active pins
        active_pins = [pin for pin, button in self.pin_buttons.items() 
                      if button.is_monitoring and button.pin_config.is_analog_input]
        
        if not active_pins:
            QMessageBox.warning(self, "No Active Sensors", 
                              "Please start monitoring and select at least one sensor before recording.")
            return
        
        # Start recording
        filename = self.data_recorder.start_recording(active_pins, self.pin_configs)
        
        # Update UI
        self.record_button.setText("Stop Recording")
        self.record_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #388E3C;
            }
        """)
        
        self.recording_status.setText(f"Recording to: {filename}")
        self.recording_status.setStyleSheet("color: #f44336; font-weight: bold;")
        
        # Disable monitoring controls during recording
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        
    def stop_recording(self):
        """Stop recording and save data"""
        if not self.data_recorder.is_recording:
            return
            
        # Stop recording and save
        saved_file = self.data_recorder.stop_recording_and_save()
        
        # Update UI
        self.record_button.setText("Start Recording")
        self.record_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        
        if saved_file:
            self.recording_status.setText(f"Recording saved: {os.path.basename(saved_file)}")
            self.recording_status.setStyleSheet("color: #4CAF50; font-weight: bold;")
            
            # Show success message
            data_points = len(self.data_recorder.recorded_data)
            QMessageBox.information(self, "Recording Saved", 
                                  f"Recording saved successfully!\n\n"
                                  f"File: {saved_file}\n"
                                  f"Data points: {data_points}\n"
                                  f"Duration: {data_points/10:.1f} seconds (approx.)")
        else:
            self.recording_status.setText("Recording cancelled")
            self.recording_status.setStyleSheet("color: #666; font-style: italic;")
        
        # Re-enable monitoring controls
        if self.daq_simulator.running:
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
        else:
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            
    def update_daq_status_display(self):
        """Update the DAQ device status display"""
        if hasattr(self, 'daq_simulator') and self.daq_simulator.daq_type != "NONE":
            status_text = f"DAQ: {self.daq_simulator.daq_type} - {self.daq_simulator.device}"
            self.daq_status.setText(status_text)
            self.daq_status.setStyleSheet("color: #4CAF50; font-weight: bold; font-size: 12px;")
        else:
            self.daq_status.setText("DAQ: No device detected")
            self.daq_status.setStyleSheet("color: #f44336; font-weight: bold; font-size: 12px;")
    
    def start_monitoring(self):
        """Start the DAQ monitoring process - Real sensors only"""
        if self.daq_simulator.daq_type == "NONE":
            QMessageBox.warning(self, "No DAQ Device", 
                               "Cannot start monitoring - no DAQ device detected!")
            return
            
        print(f"Starting real DAQ monitoring using {self.daq_simulator.daq_type} device: {self.daq_simulator.device}")
        
        # Restore plots for selected pins
        for pin_number, button in self.pin_buttons.items():
            if button.isChecked():
                pin_config = next((p for p in self.pin_configs if p.pin_number == pin_number), None)
                if pin_config and pin_config.is_analog_input:
                    button.set_monitoring(True)
                    color = self.plot_widget.add_channel(pin_number, pin_config.name, pin_config)
                    pin_config.color = color
                    self.daq_simulator.add_pin(pin_number)
        
        self.daq_simulator.start_acquisition()
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        
    def stop_monitoring(self):
        """Stop the DAQ monitoring process"""
        # Stop recording if active
        if self.data_recorder.is_recording:
            self.stop_recording()
        
        print("Stopping DAQ monitoring")
        self.daq_simulator.stop_acquisition()
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        
        # Keep pin selections but stop monitoring state
        for button in self.pin_buttons.values():
            button.set_monitoring(False)  # Stop monitoring but keep checkbox selection
            
        # Reset recording status
        self.recording_status.setText("Ready to record")
        self.recording_status.setStyleSheet("color: #666; font-style: italic;")
            
    @pyqtSlot(int, float)
    def update_plot_data(self, pin_number: int, voltage: float):
        """Update plot with new data from DAQ"""
        pin_config = next((p for p in self.pin_configs if p.pin_number == pin_number), None)
        if pin_config:
            # Calculate calibrated value
            if pin_config.calibration.is_calibrated:
                calibrated_value = PinNameEditor.apply_calibration(voltage, pin_config.calibration)
            else:
                calibrated_value = voltage
            
            # Update plot
            self.plot_widget.update_data(pin_number, voltage, pin_config)
            
            # Record data if recording is active
            if self.data_recorder.is_recording:
                self.data_recorder.add_data_point(pin_number, voltage, calibrated_value, time.time())
        
    def closeEvent(self, event):
        """Handle application close"""
        # Stop recording if active
        if self.data_recorder.is_recording:
            reply = QMessageBox.question(self, "Recording Active", 
                                       "Recording is currently active. Do you want to save the recording before closing?",
                                       QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
            
            if reply == QMessageBox.Yes:
                self.stop_recording()
            elif reply == QMessageBox.Cancel:
                event.ignore()
                return
        
        # Save application state
        self.save_state()
        
        self.daq_simulator.stop_acquisition()
        event.accept()
        
    def save_state(self):
        """Save current application state"""
        self.state_manager.save_state(self.pin_configs)

def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    # Create and show main window
    window = DAQMonitorApp()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()