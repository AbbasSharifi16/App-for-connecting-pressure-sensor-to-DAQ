#!/usr/bin/env python3
"""
Test file to isolate import issues
"""

print("Testing imports...")

try:
    import json
    print("✓ json imported successfully")
except ImportError as e:
    print(f"✗ json import failed: {e}")

try:
    import platform
    print(f"✓ platform imported successfully - System: {platform.system()}")
except ImportError as e:
    print(f"✗ platform import failed: {e}")

try:
    from ctypes import c_int, c_double, POINTER, byref
    print("✓ basic ctypes imported successfully")
except ImportError as e:
    print(f"✗ basic ctypes import failed: {e}")

# Platform-specific imports
if platform.system() == "Windows":
    try:
        from ctypes import WinDLL
        print("✓ WinDLL imported successfully (Windows)")
        WINDOWS_PLATFORM = True
    except ImportError as e:
        print(f"✗ WinDLL import failed: {e}")
        WINDOWS_PLATFORM = False
        WinDLL = None
else:
    print("✓ Non-Windows platform - skipping WinDLL")
    WINDOWS_PLATFORM = False
    WinDLL = None

try:
    from datetime import datetime, timedelta
    print("✓ datetime imported successfully")
except ImportError as e:
    print(f"✗ datetime import failed: {e}")

try:
    from typing import Dict, List, Optional
    print("✓ typing imported successfully")
except ImportError as e:
    print(f"✗ typing import failed: {e}")

try:
    from dataclasses import dataclass, asdict
    print("✓ dataclasses imported successfully")
except ImportError as e:
    print(f"✗ dataclasses import failed: {e}")

print("\nAll basic imports completed!")