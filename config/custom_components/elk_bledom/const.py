"""Constants for ELK-BLEDOM integration."""

DOMAIN = "elk_bledom"

# Bluetooth UUIDs
SERVICE_UUID = "0000fff0-0000-1000-8000-00805f9b34fb"
CHARACTERISTIC_UUID = "0000fff3-0000-1000-8000-00805f9b34fb"

# Command prefixes
CMD_PREFIX = bytearray([0x7E, 0x00])  # Standard prefix
CMD_SUFFIX = bytearray([0x00, 0xEF])  # Standard suffix

# Commands
CMD_POWER_ON = bytearray([0x7E, 0x00, 0x04, 0x01, 0x00, 0x00, 0x00, 0x00, 0xEF])
CMD_POWER_OFF = bytearray([0x7E, 0x00, 0x04, 0x00, 0x00, 0x00, 0x00, 0x00, 0xEF])

# Device name patterns
DEVICE_NAME_PATTERNS = ["ELK-BLEDOM", "BLEDOM", "Triones"]
