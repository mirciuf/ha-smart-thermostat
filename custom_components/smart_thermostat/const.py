"""Constants for Smart Thermostat integration."""

DOMAIN = "smart_thermostat"
NAME = "Smart Thermostat"
VERSION = "1.1.0"

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

# Cool type selector — "none" | "switch" | "scene" | "climate"
CONF_COOL_TYPE = "cool_type"
COOL_TYPE_NONE = "none"
COOL_TYPE_SWITCH = "switch"
COOL_TYPE_SCENE = "scene"
COOL_TYPE_CLIMATE = "climate"

# AC climate entity keys (cool only)
CONF_AC_CLIMATE_ENTITY = "ac_climate_entity"
CONF_AC_CLIMATE_COOL_TEMP = "ac_climate_cool_temp"
CONF_AC_CLIMATE_MIN_RUNTIME = "ac_climate_min_runtime"

DEFAULT_AC_CLIMATE_COOL_TEMP = 18.0
DEFAULT_AC_CLIMATE_MIN_RUNTIME = 10  # minutes

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
ATTR_COOL_TYPE = "cool_type"
ATTR_AC_CLIMATE_ENTITY = "ac_climate_entity"
ATTR_AC_CLIMATE_COOL_TEMP = "ac_climate_cool_temp"
ATTR_AC_CLIMATE_MIN_RUNTIME = "ac_climate_min_runtime"

# Presets
CONF_PRESETS = "presets"
PRESET_NONE = "none"
ATTR_PRESETS = "presets"


def resolve_cool_type(data: dict) -> str:
    """Best-effort cool_type for legacy entries created before this field existed."""
    cool_type = data.get(CONF_COOL_TYPE)
    if cool_type in (COOL_TYPE_NONE, COOL_TYPE_SWITCH, COOL_TYPE_SCENE, COOL_TYPE_CLIMATE):
        return cool_type
    if data.get(CONF_COOL_SWITCH):
        return COOL_TYPE_SWITCH
    if data.get(CONF_AC_SCENE_COOL_ON) and data.get(CONF_AC_SCENE_COOL_OFF):
        return COOL_TYPE_SCENE
    if data.get(CONF_AC_CLIMATE_ENTITY):
        return COOL_TYPE_CLIMATE
    return COOL_TYPE_NONE
