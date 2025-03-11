"""Constants for the General Thermostat helper."""

from homeassistant.components.climate import (
    PRESET_ACTIVITY,
    PRESET_AWAY,
    PRESET_COMFORT,
    PRESET_ECO,
    PRESET_HOME,
    PRESET_SLEEP,
    PRESET_BOOST,
)
from homeassistant.const import Platform

ATTR_AUTO_UPDATE_PRESET_MODES = "auto_update_preset_modes"
ATTR_PRESET_TEMPERATURES = "preset_temperatures"

DOMAIN = "general_thermostat"

PLATFORMS = [Platform.CLIMATE]

PRESET_REDUCE = "reduce"

CONF_AC_MODE = "ac_mode"
CONF_AUTO_UPDATE_PRESET_MODES = "auto_update_preset_modes"
CONF_COLD_TOLERANCE = "cold_tolerance"
CONF_HEATER = "heater"
CONF_HOT_TOLERANCE = "hot_tolerance"
CONF_MAX_TEMP = "max_temp"
CONF_MIN_DUR = "min_cycle_duration"
CONF_MIN_TEMP = "min_temp"
CONF_PRESETS = {
    p: f"{p}_temp"
    for p in (
        PRESET_AWAY,
        PRESET_COMFORT,
        PRESET_ECO,
        PRESET_HOME,
        PRESET_SLEEP,
        PRESET_ACTIVITY,
        PRESET_BOOST,
        PRESET_REDUCE,
    )
}
CONF_SENSOR = "target_sensor"
DEFAULT_TOLERANCE = 0.3

SERVICE_SET_PRESET_TEMPERATURE = "set_preset_temperature"
SERVICE_RESET_PRESET_TEMPERATURE = "reset_preset_temperature"
