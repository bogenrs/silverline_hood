"""Constants for the Silverline Hood integration."""
from datetime import timedelta

DOMAIN = "silverline_hood"
DEFAULT_NAME = "Silverline Hood"
DEFAULT_PORT = 8555
DEFAULT_UPDATE_INTERVAL = 10  # seconds

CONF_HOST = "host"
CONF_PORT = "port"
CONF_UPDATE_INTERVAL = "update_interval"

# JSON command keys - erweitert basierend auf der App-Kommunikation
CMD_MOTOR = "M"
CMD_LIGHT = "L"
CMD_RED = "R"
CMD_GREEN = "G"
CMD_BLUE = "B"
CMD_COLD_WHITE = "CW"
CMD_BRIGHTNESS = "BRG"
CMD_T = "T"
CMD_TM = "TM"
CMD_TS = "TS"
CMD_A = "A"

# Neue Parameter aus der App
CMD_LM = "LM"          # Light Mode?
CMD_CWD = "CWD"        # Cold White Direction?
CMD_RGBD = "RGBD"      # RGB Direction?
CMD_WAPS = "WAPS"      # WiFi Access Point SSID
CMD_WAPP = "WAPP"      # WiFi Access Point Password
CMD_U = "U"            # Unknown
CMD_W = "W"            # WiFi Mode (STA = Station)
CMD_WS = "WS"          # WiFi SSID

# Status query command
STATUS_QUERY = {"A": 4}

# Expected device response
DEVICE_IDENTIFIER = "okidargb"

# Motor speeds
MOTOR_OFF = 0
MOTOR_SPEED_1 = 1
MOTOR_SPEED_2 = 2
MOTOR_SPEED_3 = 3
MOTOR_SPEED_4 = 4

SPEED_LIST = ["off", "low", "medium", "high", "max"]

# Light modes (basierend auf der Log)
LIGHT_OFF = 0
LIGHT_ON = 1
LIGHT_MODE_2 = 2  # Möglicherweise ein spezieller Modus

# Update interval constraints
MIN_UPDATE_INTERVAL = 5  # seconds
MAX_UPDATE_INTERVAL = 300  # seconds

# Command line ending (Carriage Return)
CMD_LINE_ENDING = '\r'