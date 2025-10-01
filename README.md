# DAQ Pressure Sensor Monitor

[![Python](https://img.shields.io/badge/Python-3.7%2B-blue.svg)](https://www.python.org/downloads/)
[![Qt](https://img.shields.io/badge/Qt-PyQt5-green.svg)](https://pypi.org/project/PyQt5/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-lightgrey.svg)](https://github.com/yourusername/daq-pressure-monitor)

A Python application with Qt graphics for monitoring pressure sensors connected to a DAQ device. This application provides a visual representation of the DAQ pin layout and real-time plotting capabilities.

![Application Screenshot](docs/screenshot_placeholder.png)

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/yourusername/daq-pressure-monitor.git
cd daq-pressure-monitor

# Install dependencies (Ubuntu)
chmod +x setup_ubuntu.sh
./setup_ubuntu.sh

# Run the application
python3 daq_pressure_monitor.py
```

## ✨ Features

- **Visual Pin Layout**: Interactive representation of the 40-pin DAQ connector
- **Configurable Pin Names**: Editable names for each analog input pin
- **Sensor Calibration**: Linear calibration for each sensor with two-point calibration
- **Data Recording**: Record sensor data to CSV files with timestamps and calibration info
- **Plot Export**: Save plots as PDF, JPG, or PNG files with timestamp
- **Real-time Plotting**: Live data visualization with multiple channels
- **Multi-channel Support**: Plot multiple pressure sensors simultaneously
- **Toggle Channels**: Click pins to add/remove channels from the plot
- **Automatic Unit Conversion**: Applies calibration to convert voltage to physical units
- **Simulated Data**: Built-in data simulator for testing (replace with real DAQ interface)

## 📋 Pin Configuration

The application supports your DAQ configuration:

### Single-Ended Mode (8 Analog Inputs)
- **Pins 1, 2, 4, 5, 7, 8, 10, 11**: Analog inputs (CH0-CH7)
- **11-bit resolution**
- Default names: Pressure_1 through Pressure_8

### Differential Mode (4 Analog Inputs)
- **Pins 1&2, 4&5, 7&8, 10&11**: Differential pairs (CH0-CH3)
- **12-bit resolution**

## DAQ Device Setup

The application supports real DAQ devices and will automatically detect them. If no real DAQ is found, it will run in simulation mode.

### Supported DAQ Devices

#### National Instruments (NI) DAQ
1. Install NI-DAQmx driver from [National Instruments website](https://www.ni.com/en-us/support/downloads/drivers/download.ni-daqmx.html)
2. Install Python library:
   ```bash
   pip install nidaqmx
   ```

#### Measurement Computing DAQ
1. Install MCC DAQ software from [Measurement Computing website](https://www.mccdaq.com/software-downloads)
2. Install Python library:
   ```bash
   pip install mcculw
   ```

#### Generic USB DAQ
For other USB DAQ devices, you may need device-specific drivers or use:
```bash
pip install pyusb
```

### DAQ Connection
1. Connect your DAQ device via USB
2. Ensure drivers are properly installed
3. Run the application - it will automatically detect and configure your DAQ
4. The application will display which DAQ type was detected in the console

### Pin Mapping
- Application pins 1-8 map to DAQ analog input channels AI0-AI7
- Ensure your pressure sensors are connected to the corresponding analog input channels
- Configure voltage range in your DAQ software if needed (typically 0-5V or ±10V)

## Installation

### Ubuntu Setup

1. **Clone or download the files to your system**

2. **Make the setup script executable and run it:**
   ```bash
   chmod +x setup_ubuntu.sh
   ./setup_ubuntu.sh
   ```

3. **Alternative manual installation:**
   ```bash
   # Update system
   sudo apt update
   
   # Install Python and Qt5
   sudo apt install python3 python3-pip python3-pyqt5 python3-pyqt5-dev
   
   # Install Python dependencies
   pip3 install -r requirements.txt
   ```

## 🎮 Usage

### Starting the Application

```bash
python3 daq_pressure_monitor.py
```

### Using the Interface

1. **Configure Pin Names**:
   - Use the "Pin Configuration" section on the left to rename analog input pins
   - Default names are Pressure_1, Pressure_2, etc.

2. **Calibrate Sensors**:
   - Click the "Cal" button next to each sensor name
   - Enter two calibration points (physical value ~ voltage)
   - Example: 1 m ~ 2.3 V, 2 m ~ 4.1 V
   - Enable calibration checkbox to activate
   - Calibrated sensors show green "Cal" button and display physical units

3. **Start Monitoring**:
   - Click "Start Monitoring" to begin data acquisition
   - The simulator will generate realistic voltage data

4. **Start Data Recording** (Optional):
   - Click "Start Recording" in the top control bar
   - Recording captures data from all active sensors
   - Status shows recording filename and state

5. **Select Channels**:
   - Click on blue analog input pin buttons to add them to the plot
   - Active pins will turn green and appear in the real-time plot
   - Click again to remove a channel from the plot

6. **View Real-time Data**:
   - The right panel shows real-time sensor data
   - Calibrated sensors display in physical units, uncalibrated in volts
   - Multiple channels can be plotted simultaneously
   - Each channel has a different color and is labeled in the legend

7. **Save Plots**:
   - Click the "Save Plot" button above the graph
   - Choose from PDF, JPG, or PNG format
   - Files are automatically named with timestamp
   - PDF export includes high-quality vector graphics (requires matplotlib)

8. **Stop Data Recording**:
   - Click "Stop Recording" to end data capture
   - Choose save location for CSV file
   - CSV includes timestamps, raw voltages, and calibrated values

9. **Stop Monitoring**:
   - Click "Stop Monitoring" to halt data acquisition
   - This will automatically stop any active recording
   - All plots and pin states will be reset

## 🔧 Customization

### Data Recording

The application records data in CSV format with comprehensive information:

1. **CSV Structure**:
   - **Headers**: Sensor configuration and calibration info
   - **Timestamps**: Both Unix timestamp and relative time
   - **Raw Data**: Original voltage readings
   - **Calibrated Data**: Physical units (if calibrated)
   - **Metadata**: Sensor names, pin numbers, units

2. **File Format Example**:
   ```csv
   # DAQ Sensor Recording
   # Generated: 2025-10-01 14:30:52
   # Pin 1 (Pressure_1): Calibrated to psi
   #   Calibration: 0 psi @ 1.0 V, 100 psi @ 5.0 V
   Timestamp (Unix),Relative Time (s),Pin Number,Sensor Name,Voltage (V),Calibrated Value (psi)
   1696176652.123456,0.000,1,Pressure_1,2.500,37.500
   ```

### Sensor Calibration

The application supports linear calibration for each sensor:

1. **Two-Point Calibration**: Enter two known calibration points
   - Physical value (your measurement unit) 
   - Corresponding voltage reading
   - Example: 0 psi ~ 1.0 V, 100 psi ~ 5.0 V

2. **Linear Transformation**: The application automatically calculates:
   ```
   Physical_Value = slope × Voltage + intercept
   ```

3. **Mixed Units**: Different sensors can have different units (m, psi, Pa, etc.)

### Connecting Real DAQ Hardware

Replace the `DAQSimulator` class with your actual DAQ interface:

```python
# Example for a real DAQ implementation
class RealDAQ(QThread):
    data_ready = pyqtSignal(int, float)
    
    def __init__(self):
        super().__init__()
        # Initialize your DAQ hardware here
        
    def read_channel(self, channel):
        # Implement actual DAQ reading
        pass
```

### Modifying Pin Layout

To customize the pin configuration, edit the `create_pin_configs()` method in the `DAQMonitorApp` class.

### Changing Plot Settings

Modify the `PlotWidget` class to adjust:
- Sample rate
- Buffer size
- Plot appearance
- Units and scaling

## 📁 File Structure

```
daq-pressure-monitor/
├── daq_pressure_monitor.py    # Main application file
├── requirements.txt           # Python dependencies
├── setup_ubuntu.sh           # Ubuntu setup script
├── README.md                 # This file
├── LICENSE                   # MIT license
├── CONTRIBUTING.md           # Contribution guidelines
├── CHANGELOG.md              # Version history
├── .gitignore               # Git ignore file
└── docs/                    # Documentation assets
```

## 📦 Dependencies

- **PyQt5**: GUI framework
- **pyqtgraph**: Real-time plotting library
- **numpy**: Numerical computing
- **matplotlib**: High-quality plot export (PDF support)

## 🐛 Troubleshooting

### Common Issues

1. **Qt5 not found**:
   ```bash
   sudo apt install python3-pyqt5-dev qttools5-dev-tools
   ```

2. **Permission denied for setup script**:
   ```bash
   chmod +x setup_ubuntu.sh
   ```

3. **Import errors**:
   ```bash
   pip3 install --user -r requirements.txt
   ```

4. **Matplotlib not found (for PDF export)**:
   ```bash
   pip3 install matplotlib
   ```
   
   Note: JPG and PNG export work without matplotlib using pyqtgraph

### Performance Optimization

- Adjust `max_points` in `PlotWidget` to control memory usage
- Modify `sample_rate` in `DAQSimulator` for different update frequencies
- Use hardware-accelerated OpenGL for better plot performance

## 🏗️ Development

### Key Classes

- **`DAQMonitorApp`**: Main application window
- **`PinButton`**: Custom button representing DAQ pins
- **`PlotWidget`**: Real-time plotting component
- **`DAQSimulator`**: Data acquisition simulator
- **`PinNameEditor`**: Pin configuration interface
- **`DataRecorder`**: CSV data recording system
- **`CalibrationDialog`**: Sensor calibration interface

### Signal Flow

1. User clicks pin button → `toggle_pin()`
2. Pin added to simulator → `DAQSimulator.add_pin()`
3. Simulator generates data → `data_ready` signal
4. Plot updated → `update_plot_data()`
5. Data recorded → `DataRecorder.add_data_point()`

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details on how to contribute to this project.

### Areas for Contribution

- Real DAQ hardware integration
- Additional export formats
- Performance optimization
- Cross-platform testing
- Additional calibration methods
- Data analysis tools

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with PyQt5 and PyQtGraph
- Inspired by industrial DAQ monitoring needs
- Designed for scientific and engineering applications

## 📞 Support

For questions, issues, or feature requests:

1. Check the [troubleshooting section](#-troubleshooting)
2. Search [existing issues](https://github.com/yourusername/daq-pressure-monitor/issues)
3. Create a [new issue](https://github.com/yourusername/daq-pressure-monitor/issues/new)

---

**Note**: Remember to replace `yourusername` in the GitHub URLs with your actual GitHub username when you create the repository.