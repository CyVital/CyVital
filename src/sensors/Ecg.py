import dwfpy as dwf

# List available devices
devices = dwf.Device.enumerate()
if not devices:
    raise RuntimeError("No Digilent WaveForms device found. Check connections.")

# Open the first detected device
device = dwf.Device()  # No need for `.open()`

# Debugging output
print(f"Opened Device: {device}")
print(dwf.FDwfGetVersion())
if device.digital_io is None:
    raise RuntimeError("Digital IO not available. Check if the device supports it.")

# Configure digital I/O (set a pin high)
try:
    digital_io = device.digital_io
    digital_io[0].setup(direction="output")  # Set first digital pin as output
    digital_io[0].value = 1  # Set the pin HIGH
    print("Digital IO configured successfully. Pin 0 is HIGH.")
except Exception as e:
    print(f"Failed to configure Digital IO: {e}")
