"""Constants for the Silverline Hood integration."""
DOMAIN = "silverline_hood"
DEFAULT_PORT = 8555

CONF_HOST = "host"
CONF_PORT = "port"

CMD_MOTOR = "M"
CMD_LIGHT = "L"

# Motor speeds - KORRIGIERT basierend auf Ihren Erkenntnissen
MOTOR_OFF = 1      # M:1 = AUS
MOTOR_SPEED_1 = 2  # M:2 = Stufe 1
MOTOR_SPEED_2 = 3  # M:3 = Stufe 2  
MOTOR_SPEED_3 = 4  # M:4 = Stufe 3
MOTOR_SPEED_4 = 5  # M:5 = Stufe 4

SPEED_LIST = ["off", "low", "medium", "high", "max"]