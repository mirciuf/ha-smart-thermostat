"""Constants for Smart Thermostat integration."""

DOMAIN = "smart_thermostat"
NAME = "Smart Thermostat"
VERSION = "1.0.0"

# Config keys
CONF_THERMOSTAT_NAME = "thermostat_name"
CONF_TEMP_SENSOR = "temp_sensor"
CONF_HEAT_SWITCH = "heat_switch"
CONF_COOL_SWITCH = "cool_switch"
CONF_WINDOW_SENSOR = "window_sensor"
CONF_WINDOW_SENSOR_2 = "window_sensor_2"
CONF_OUTDOOR_SENSOR = "outdoor_sensor"
CONF_TARGET_TEMP = "target_temp"
CONF_HYSTERESIS = "hysteresis"
CONF_OUTDOOR_TEMP_THRESHOLD = "outdoor_temp_threshold"
CONF_MIN_TEMP = "min_temp"
CONF_MAX_TEMP = "max_temp"

# AC Scene keys (cool only)
CONF_AC_SCENE_COOL_ON = "ac_scene_cool_on"
CONF_AC_SCENE_COOL_OFF = "ac_scene_cool_off"

# Config keys - temp step
CONF_TEMP_STEP = "temp_step"
DEFAULT_TEMP_STEP = 0.5

# Defaults
DEFAULT_TARGET_TEMP = 21.0
DEFAULT_HYSTERESIS = 0.5
DEFAULT_OUTDOOR_THRESHOLD = 20.0
DEFAULT_MIN_TEMP = 5.0
DEFAULT_MAX_TEMP = 35.0

# Attributes
ATTR_HYSTERESIS = "hysteresis"
ATTR_OUTDOOR_THRESHOLD = "outdoor_temp_threshold"
ATTR_WINDOW_OPEN = "window_open"
ATTR_OUTDOOR_TEMP = "outdoor_temperature"
ATTR_HEAT_SWITCH = "heat_switch"
ATTR_COOL_SWITCH = "cool_switch"
ATTR_TEMP_SENSOR = "temp_sensor"
ATTR_AC_SCENE_COOL_ON = "ac_scene_cool_on"
ATTR_AC_SCENE_COOL_OFF = "ac_scene_cool_off"

# Presets
CONF_PRESETS = "presets"
PRESET_NONE = "none"
ATTR_PRESETS = "presets"
