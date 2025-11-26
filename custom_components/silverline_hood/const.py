"""Constants for the Silverline Hood integration."""
from datetime import timedelta

DOMAIN = "silverline_hood"
DEFAULT_NAME = "Silverline Hood"
DEFAULT_PORT = 23
DEFAULT_UPDATE_INTERVAL = 10  # seconds

CONF_HOST = "host"
CONF_PORT = "port"
CONF_UPDATE_INTERVAL = "update_interval"

# JSON command keys
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

# Status query command
STATUS_QUERY = {"A": 4}

# Motor speeds
MOTOR_OFF = 0
MOTOR_SPEED_1 = 1
MOTOR_SPEED_2 = 2
MOTOR_SPEED_3 = 3
MOTOR_SPEED_4 = 4

SPEED_LIST = ["off", "low", "medium", "high", "max"]

# Update interval constraints
MIN_UPDATE_INTERVAL = 5  # seconds
MAX_UPDATE_INTERVAL = 300  # seconds