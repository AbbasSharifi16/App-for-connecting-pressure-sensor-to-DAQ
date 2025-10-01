# Contributing to DAQ Pressure Sensor Monitor

Thank you for your interest in contributing to the DAQ Pressure Sensor Monitor project! We welcome contributions from the community.

## How to Contribute

### Reporting Issues
- Use the GitHub issue tracker to report bugs
- Include detailed description and steps to reproduce
- Specify your operating system and Python version
- Include error messages and stack traces if applicable

### Suggesting Features
- Open an issue with the "enhancement" label
- Describe the feature and its use case
- Explain how it would benefit users

### Code Contributions

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature-name`
3. **Make your changes** following the coding standards below
4. **Test thoroughly** on your target platform
5. **Commit with clear messages**: `git commit -m "Add feature: description"`
6. **Push to your fork**: `git push origin feature-name`
7. **Create a Pull Request**

## Coding Standards

### Python Style
- Follow PEP 8 style guidelines
- Use meaningful variable and function names
- Add docstrings to classes and functions
- Keep functions focused and modular

### Code Organization
- Keep classes in logical order
- Group related functionality together
- Use type hints where appropriate
- Handle exceptions gracefully

### Testing
- Test on both Windows and Linux if possible
- Verify Qt interface functionality
- Test with and without optional dependencies
- Include sample data for testing

### Documentation
- Update README.md for new features
- Add inline comments for complex logic
- Update requirements.txt if adding dependencies
- Include examples in docstrings

## Development Setup

1. **Clone your fork**:
   ```bash
   git clone https://github.com/yourusername/daq-pressure-monitor.git
   cd daq-pressure-monitor
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or
   venv\Scripts\activate     # Windows
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**:
   ```bash
   python daq_pressure_monitor.py
   ```

## Areas for Contribution

### High Priority
- Real DAQ hardware integration
- Additional export formats
- Performance optimization
- Cross-platform testing

### Medium Priority
- Additional calibration methods (polynomial, etc.)
- Data analysis tools
- Configuration file support
- Plugin architecture

### Low Priority
- UI themes and customization
- Advanced plotting options
- Data streaming capabilities
- Remote monitoring features

## Pull Request Guidelines

- **One feature per PR**: Keep pull requests focused
- **Clear description**: Explain what changes and why
- **Test coverage**: Ensure changes don't break existing functionality
- **Documentation**: Update relevant documentation
- **Backwards compatibility**: Maintain compatibility when possible

## Questions?

Feel free to open an issue for questions about contributing or development setup.

Thank you for contributing to the DAQ Pressure Sensor Monitor project!