"""Constants for the Silverline Hood integration."""
DOMAIN = "silverline_hood"
DEFAULT_PORT = 8555
DEFAULT_UPDATE_INTERVAL = 10  # Diese Zeile fehlte!

CONF_HOST = "host"
CONF_PORT = "port"
CONF_UPDATE_INTERVAL = "update_interval"  # Diese auch

# JSON command keys - Basis
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

# Erweiterte Daten aus Wireshark
CMD_LIGHT_MODE = "LM"       # Light Mode
CMD_CW_DIRECTION = "CWD"    # Cold White Direction
CMD_RGB_DIRECTION = "RGBD"  # RGB Direction
CMD_WIFI_AP_SSID = "WAPS"   # WiFi Access Point SSID
CMD_WIFI_AP_PASS = "WAPP"   # WiFi Access Point Password
CMD_UNKNOWN_U = "U"         # Unknown parameter
CMD_WIFI_MODE = "W"         # WiFi Mode (STA = Station)
CMD_WIFI_SSID = "WS"        # Current WiFi SSID

# Motor speeds - korrigiert
MOTOR_OFF = 1
MOTOR_SPEED_1 = 2
MOTOR_SPEED_2 = 3  
MOTOR_SPEED_3 = 4
MOTOR_SPEED_4 = 5

SPEED_LIST = ["off", "low", "medium", "high", "max"]

# Status query command
STATUS_QUERY = {"A": 4}
DEVICE_IDENTIFIER = "okidargb"
CMD_LINE_ENDING = '\r'

# Update interval constraints
MIN_UPDATE_INTERVAL = 5  # seconds
MAX_UPDATE_INTERVAL = 300  # seconds