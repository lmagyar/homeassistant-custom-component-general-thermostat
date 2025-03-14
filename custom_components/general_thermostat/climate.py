"""Adds support for general thermostat units."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from datetime import datetime, timedelta
import logging
import math
from typing import Any, final

from propcache.api import cached_property
import voluptuous as vol

from homeassistant.components.climate import (
    ATTR_PRESET_MODE,
    ATTR_PRESET_MODES,
    PLATFORM_SCHEMA as CLIMATE_PLATFORM_SCHEMA,
    PRESET_NONE,
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_TEMPERATURE,
    CONF_ICON,
    CONF_NAME,
    CONF_UNIQUE_ID,
    EVENT_HOMEASSISTANT_START,
    PRECISION_HALVES,
    PRECISION_TENTHS,
    PRECISION_WHOLE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    UnitOfTemperature,
)
from homeassistant.core import (
    DOMAIN as HOMEASSISTANT_DOMAIN,
    CoreState,
    Event,
    EventStateChangedData,
    HomeAssistant,
    State,
    callback,
)
from homeassistant.exceptions import ConditionError, ServiceValidationError
from homeassistant.helpers import condition, config_validation as cv, entity_platform
from homeassistant.helpers.device import async_device_info_to_link_from_entity
from homeassistant.helpers.entity_platform import (
    AddConfigEntryEntitiesCallback,
    AddEntitiesCallback,
)
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType, VolDictType

from .const import (
    ATTR_AUTO_UPDATE_PRESET_MODES,
    ATTR_COLD_TOLERANCE,
    ATTR_HOT_TOLERANCE,
    ATTR_PRESET_TEMPERATURES,
    CONF_AC_MODE,
    CONF_AUTO_UPDATE_PRESET_MODES,
    CONF_COLD_TOLERANCE,
    CONF_HEATER,
    CONF_HOT_TOLERANCE,
    CONF_MAX_TEMP,
    CONF_MIN_DUR,
    CONF_MIN_TEMP,
    CONF_PRESETS,
    CONF_SENSOR,
    DEFAULT_TOLERANCE,
    DOMAIN,
    SERVICE_SET_PRESET_TEMPERATURE,
    SERVICE_RESET_PRESET_TEMPERATURE,
    SERVICE_SET_TOLERANCE,
)

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "General Thermostat"

CONF_INITIAL_HVAC_MODE = "initial_hvac_mode"
CONF_KEEP_ALIVE = "keep_alive"
CONF_PRECISION = "precision"
CONF_TARGET_TEMP = "target_temp"
CONF_TEMP_STEP = "target_temp_step"


PRESETS_SCHEMA: VolDictType = {
    vol.Optional(v): vol.Coerce(float) for v in CONF_PRESETS.values()
}

PLATFORM_SCHEMA_COMMON = vol.Schema(
    {
        vol.Required(CONF_HEATER): cv.entity_id,
        vol.Required(CONF_SENSOR): cv.entity_id,
        vol.Optional(CONF_AC_MODE): cv.boolean,
        vol.Optional(CONF_AUTO_UPDATE_PRESET_MODES): vol.All(
            cv.ensure_list_csv, [vol.In(CONF_PRESETS.keys())]
        ),
        vol.Optional(CONF_MAX_TEMP): vol.Coerce(float),
        vol.Optional(CONF_MIN_DUR): cv.positive_time_period,
        vol.Optional(CONF_MIN_TEMP): vol.Coerce(float),
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_COLD_TOLERANCE): vol.Coerce(float),
        vol.Optional(CONF_HOT_TOLERANCE): vol.Coerce(float),
        vol.Optional(CONF_TARGET_TEMP): vol.Coerce(float),
        vol.Optional(CONF_KEEP_ALIVE): cv.positive_time_period,
        vol.Optional(CONF_INITIAL_HVAC_MODE): vol.In(
            [HVACMode.COOL, HVACMode.HEAT, HVACMode.OFF]
        ),
        vol.Optional(CONF_PRECISION): vol.All(
            vol.Coerce(float),
            vol.In([PRECISION_TENTHS, PRECISION_HALVES, PRECISION_WHOLE]),
        ),
        vol.Optional(CONF_TEMP_STEP): vol.All(
            vol.In([PRECISION_TENTHS, PRECISION_HALVES, PRECISION_WHOLE])
        ),
        vol.Optional(CONF_UNIQUE_ID): cv.string,
        vol.Optional(CONF_ICON): cv.icon,
        **PRESETS_SCHEMA,
    }
)


PLATFORM_SCHEMA = CLIMATE_PLATFORM_SCHEMA.extend(PLATFORM_SCHEMA_COMMON.schema)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Initialize config entry."""
    await _async_setup_config(
        hass,
        PLATFORM_SCHEMA_COMMON(dict(config_entry.options)),
        config_entry.entry_id,
        async_add_entities,
    )


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the general thermostat platform."""
    await _async_setup_config(
        hass, config, config.get(CONF_UNIQUE_ID), async_add_entities
    )


async def _async_setup_config(
    hass: HomeAssistant,
    config: Mapping[str, Any],
    unique_id: str | None,
    async_add_entities: AddEntitiesCallback | AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the general thermostat platform."""

    name: str = config[CONF_NAME]
    heater_entity_id: str = config[CONF_HEATER]
    sensor_entity_id: str = config[CONF_SENSOR]
    min_temp: float | None = config.get(CONF_MIN_TEMP)
    max_temp: float | None = config.get(CONF_MAX_TEMP)
    target_temp: float | None = config.get(CONF_TARGET_TEMP)
    ac_mode: bool | None = config.get(CONF_AC_MODE)
    auto_update_preset_modes: list[str] | None = config.get(CONF_AUTO_UPDATE_PRESET_MODES)
    min_cycle_duration: timedelta | None = config.get(CONF_MIN_DUR)
    cold_tolerance: float | None = config[CONF_COLD_TOLERANCE]
    hot_tolerance: float | None = config[CONF_HOT_TOLERANCE]
    keep_alive: timedelta | None = config.get(CONF_KEEP_ALIVE)
    initial_hvac_mode: HVACMode | None = config.get(CONF_INITIAL_HVAC_MODE)
    presets: dict[str, float] = {
        key: config[value] for key, value in CONF_PRESETS.items() if value in config
    }
    precision: float | None = config.get(CONF_PRECISION)
    target_temperature_step: float | None = config.get(CONF_TEMP_STEP)
    unit = hass.config.units.temperature_unit
    icon: str | None = config.get(CONF_ICON)

    if auto_update_preset_modes is not None:
        if any(p not in presets.keys() for p in auto_update_preset_modes):
            _LOGGER.error(
                "Preset(s) in auto_update_preset_modes that are not valid preset(s) for this thermostat (there is no initial temperature defined for these preset(s)): %s",
                ", ".join([p for p in auto_update_preset_modes if p not in presets.keys()]))
            auto_update_preset_modes = [p for p in auto_update_preset_modes if p in presets.keys()]

    async_add_entities(
        [
            GeneralThermostat(
                hass,
                name,
                heater_entity_id,
                sensor_entity_id,
                min_temp,
                max_temp,
                target_temp,
                ac_mode,
                auto_update_preset_modes,
                min_cycle_duration,
                cold_tolerance,
                hot_tolerance,
                keep_alive,
                initial_hvac_mode,
                presets,
                precision,
                target_temperature_step,
                unit,
                unique_id,
                icon,
            )
        ]
    )

    platform = entity_platform.async_get_current_platform()

    platform.async_register_entity_service(
        SERVICE_SET_PRESET_TEMPERATURE,
        {
            vol.Required(ATTR_PRESET_MODE): cv.string,
            vol.Required(ATTR_TEMPERATURE): vol.Coerce(float),
        },
        "async_handle_set_preset_temperature_service",
        [ClimateEntityFeature.PRESET_MODE, ClimateEntityFeature.TARGET_TEMPERATURE],
    )

    platform.async_register_entity_service(
        SERVICE_RESET_PRESET_TEMPERATURE,
        {
            vol.Optional(ATTR_PRESET_MODE): cv.string,
        },
        "async_handle_reset_preset_temperature_service",
        [ClimateEntityFeature.PRESET_MODE, ClimateEntityFeature.TARGET_TEMPERATURE],
    )

    platform.async_register_entity_service(
        SERVICE_SET_TOLERANCE,
        {
            vol.Optional(ATTR_COLD_TOLERANCE): vol.Coerce(float),
            vol.Optional(ATTR_HOT_TOLERANCE): vol.Coerce(float),
        },
        "async_handle_set_tolerance_service",
        [ClimateEntityFeature.TARGET_TEMPERATURE],
    )


CACHED_PROPERTIES_WITH_ATTR_ = {
    ATTR_AUTO_UPDATE_PRESET_MODES,
    ATTR_COLD_TOLERANCE,
    ATTR_HOT_TOLERANCE,
    ATTR_PRESET_TEMPERATURES,
}

class GeneralThermostat(ClimateEntity, RestoreEntity, cached_properties=CACHED_PROPERTIES_WITH_ATTR_):
    """Representation of a General Thermostat device."""

    _attr_auto_update_preset_modes: list[str]
    _attr_cold_tolerance: float | None
    _attr_hot_tolerance: float | None
    _attr_preset_temperatures: list[float]

    _attr_should_poll = False
    _attr_translation_key = "general_thermostat"

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return entity specific state attributes."""
        supported_features = self.supported_features

        data = {
            ATTR_COLD_TOLERANCE: self.cold_tolerance,
            ATTR_HOT_TOLERANCE: self.hot_tolerance,
        }

        if ClimateEntityFeature.PRESET_MODE in supported_features:
            data[ATTR_AUTO_UPDATE_PRESET_MODES] = self.auto_update_preset_modes
            data[ATTR_PRESET_TEMPERATURES] = self.preset_temperatures

        return data

    @cached_property
    def cold_tolerance(self) -> float:
        """Return cold tolerance."""
        return self._attr_cold_tolerance

    @cached_property
    def hot_tolerance(self) -> float:
        """Return hot tolerance."""
        return self._attr_hot_tolerance

    @cached_property
    def auto_update_preset_modes(self) -> list[str] | None:
        """Return a list of auto updated preset modes.

        Requires ClimateEntityFeature.PRESET_MODE.
        """
        return self._attr_auto_update_preset_modes

    @cached_property
    def preset_temperatures(self) -> list[float] | None:
        """Return a list of available preset temperatures.

        Requires ClimateEntityFeature.PRESET_MODE.
        """
        return self._attr_preset_temperatures

    def __init__(
        self,
        hass: HomeAssistant,
        name: str,
        heater_entity_id: str,
        sensor_entity_id: str,
        min_temp: float | None,
        max_temp: float | None,
        target_temp: float | None,
        ac_mode: bool | None,
        auto_update_preset_modes: list[str] | None,
        min_cycle_duration: timedelta | None,
        cold_tolerance: float | None,
        hot_tolerance: float | None,
        keep_alive: timedelta | None,
        initial_hvac_mode: HVACMode | None,
        presets: dict[str, float],
        precision: float | None,
        target_temperature_step: float | None,
        unit: UnitOfTemperature,
        unique_id: str | None,
        icon: str | None,
    ) -> None:
        """Initialize the thermostat."""
        self._attr_name = name
        self.heater_entity_id = heater_entity_id
        self.sensor_entity_id = sensor_entity_id
        self._attr_device_info = async_device_info_to_link_from_entity(
            hass,
            heater_entity_id,
        )
        self.ac_mode = ac_mode
        self.min_cycle_duration = min_cycle_duration
        if cold_tolerance is not None:
            self._attr_cold_tolerance = abs(cold_tolerance)
        if hot_tolerance is not None:
            self._attr_hot_tolerance = abs(hot_tolerance)
        self._keep_alive = keep_alive
        self._attr_hvac_mode = initial_hvac_mode
        if precision is not None:
            self._attr_precision = precision
        self._attr_target_temperature_step = target_temperature_step or self.precision
        if self.ac_mode:
            self._attr_hvac_modes = [HVACMode.COOL, HVACMode.OFF]
        else:
            self._attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF]
        self._active = False
        self._temp_lock = asyncio.Lock()
        if min_temp is not None:
            self._attr_min_temp = min_temp
        if max_temp is not None:
            self._attr_max_temp = max_temp
        self._attr_preset_mode = PRESET_NONE
        self._attr_target_temperature = target_temp
        self._attr_temperature_unit = unit
        self._attr_unique_id = unique_id
        self._attr_icon = icon
        self._attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE
            | ClimateEntityFeature.TURN_OFF
            | ClimateEntityFeature.TURN_ON
        )
        self._attr_auto_update_preset_modes = auto_update_preset_modes if auto_update_preset_modes is not None else list(presets.keys())
        if len(presets):
            self._attr_supported_features |= ClimateEntityFeature.PRESET_MODE
            self._attr_preset_modes = [PRESET_NONE, *presets.keys()]
            self._attr_preset_temperatures = [target_temp, *presets.values()]
        else:
            self._attr_preset_modes = [PRESET_NONE]
            self._attr_preset_temperatures = [target_temp]
        self._presets = presets

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added."""
        await super().async_added_to_hass()

        # Add listener
        self.async_on_remove(
            async_track_state_change_event(
                self.hass, [self.sensor_entity_id], self._async_sensor_changed
            )
        )
        self.async_on_remove(
            async_track_state_change_event(
                self.hass, [self.heater_entity_id], self._async_switch_changed
            )
        )

        if self._keep_alive:
            self.async_on_remove(
                async_track_time_interval(
                    self.hass, self._async_control_heating, self._keep_alive
                )
            )

        new_preset_temperatures = self._attr_preset_temperatures.copy()

        # Check If we have an old state
        if (old_state := await self.async_get_last_state()) is not None:
            if (self._attr_target_temperature is None
                and (old_attr := old_state.attributes.get(ATTR_TEMPERATURE)) is not None
            ):
                self._attr_target_temperature = float(old_attr)
            if (self._attr_cold_tolerance is None
                and (old_attr := old_state.attributes.get(ATTR_COLD_TOLERANCE)) is not None
            ):
                self._attr_cold_tolerance = abs(float(old_attr))
            if (self._attr_hot_tolerance is None
                and (old_attr := old_state.attributes.get(ATTR_HOT_TOLERANCE)) is not None
            ):
                self._attr_hot_tolerance = abs(float(old_attr))
            if (
                self.preset_modes
                and old_state.attributes.get(ATTR_PRESET_MODE) in self.preset_modes
            ):
                self._attr_preset_mode = old_state.attributes.get(ATTR_PRESET_MODE)
            if (
                (old_preset_modes := old_state.attributes.get(ATTR_PRESET_MODES)) is not None
                and (old_preset_temperatures := old_state.attributes.get(ATTR_PRESET_TEMPERATURES)) is not None
            ):
                for mode, temp in zip(old_preset_modes, old_preset_temperatures):
                    if mode in self._attr_preset_modes and temp:
                        new_preset_temperatures[self._attr_preset_modes.index(mode)] = float(temp)
            if not self._attr_hvac_mode and old_state.state:
                self._attr_hvac_mode = HVACMode(old_state.state)

        # No previous state, try and restore defaults
        if self._attr_target_temperature is None:
            if self.ac_mode:
                self._attr_target_temperature = self.max_temp
            else:
                self._attr_target_temperature = self.min_temp
            _LOGGER.warning(
                "No previously saved target temperature, setting to %s", self._attr_target_temperature
            )
        if self._attr_cold_tolerance is None:
            self._attr_cold_tolerance = DEFAULT_TOLERANCE
            _LOGGER.warning(
                "No previously saved cold tolerance, setting to %f", self._attr_cold_tolerance
            )
        if self._attr_hot_tolerance is None:
            self._attr_hot_tolerance = DEFAULT_TOLERANCE
            _LOGGER.warning(
                "No previously saved hot tolerance, setting to %f", self._attr_hot_tolerance
            )

        new_preset_temperatures[self._attr_preset_modes.index(self._attr_preset_mode)] = self._attr_target_temperature
        if not new_preset_temperatures[0]:
            new_preset_temperatures[0] = self.max_temp if self.ac_mode else self.min_temp
            _LOGGER.warning(
                "No previously saved 'none' preset temperature, setting to %s", new_preset_temperatures[0]
            )

        # Attribute setting is required by @cached_property
        if new_preset_temperatures != self._attr_preset_temperatures:
            self._attr_preset_temperatures = new_preset_temperatures

        # Set default state to off
        if not self._attr_hvac_mode:
            self._attr_hvac_mode = HVACMode.OFF

        @callback
        def _async_startup(_: Event | None = None) -> None:
            """Init on startup."""
            sensor_state = self.hass.states.get(self.sensor_entity_id)
            if sensor_state and sensor_state.state not in (
                STATE_UNAVAILABLE,
                STATE_UNKNOWN,
            ):
                self._async_update_temp(sensor_state)
                self.async_write_ha_state()
            switch_state = self.hass.states.get(self.heater_entity_id)
            if switch_state and switch_state.state not in (
                STATE_UNAVAILABLE,
                STATE_UNKNOWN,
            ):
                self.hass.async_create_task(
                    self._check_switch_initial_state(), eager_start=True
                )

        if self.hass.state is CoreState.running:
            _async_startup()
        else:
            self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_START, _async_startup)

    def _set_attr_preset_mode_based_on_target_temp(self) -> None:
        presets_inv = {v: k for v, k in zip(self._attr_preset_temperatures, self._attr_preset_modes) if k != PRESET_NONE and k not in self._attr_auto_update_preset_modes}
        self._attr_preset_mode = presets_inv.get(self._attr_target_temperature, PRESET_NONE)

    def _set_attr_preset_temperatures(self, preset_mode: str, temperature: float) -> None:
        index = self._attr_preset_modes.index(preset_mode)
        if self._attr_preset_temperatures[index] != temperature:
            new_preset_temperatures = self._attr_preset_temperatures.copy()
            new_preset_temperatures[index] = temperature
            self._attr_preset_temperatures = new_preset_temperatures

    @property
    def hvac_action(self) -> HVACAction:
        """Return the current running hvac operation if supported.

        Need to be one of CURRENT_HVAC_*.
        """
        if self._attr_hvac_mode == HVACMode.OFF:
            return HVACAction.OFF
        if not self._is_device_active:
            return HVACAction.IDLE
        if self.ac_mode:
            return HVACAction.COOLING
        return HVACAction.HEATING

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set hvac mode."""
        if hvac_mode == HVACMode.HEAT:
            self._attr_hvac_mode = HVACMode.HEAT
            await self._async_control_heating(force=True)
        elif hvac_mode == HVACMode.COOL:
            self._attr_hvac_mode = HVACMode.COOL
            await self._async_control_heating(force=True)
        elif hvac_mode == HVACMode.OFF:
            self._attr_hvac_mode = HVACMode.OFF
            if self._is_device_active:
                await self._async_heater_turn_off()
        else:
            _LOGGER.error("Unrecognized hvac mode: %s", hvac_mode)
            return
        # Ensure we update the current operation after changing the mode
        self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        if (temperature := kwargs.get(ATTR_TEMPERATURE)) is None:
            return

        self._attr_target_temperature = temperature
        preset_mode_to_update_its_temperature = self._attr_preset_mode
        if (self._attr_preset_mode == PRESET_NONE
            or self._attr_preset_mode not in self._attr_auto_update_preset_modes
        ):
            # In case of none and any non-auto-update presets, we always update the none preset (whether we jump in or out the preset, is not important)
            preset_mode_to_update_its_temperature = PRESET_NONE
            self._set_attr_preset_mode_based_on_target_temp()
        self._set_attr_preset_temperatures(preset_mode_to_update_its_temperature, temperature)
        await self._async_control_heating(force=True)
        self.async_write_ha_state()

    async def _async_sensor_changed(self, event: Event[EventStateChangedData]) -> None:
        """Handle temperature changes."""
        new_state = event.data["new_state"]
        if new_state is None or new_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return

        self._async_update_temp(new_state)
        await self._async_control_heating()
        self.async_write_ha_state()

    async def _check_switch_initial_state(self) -> None:
        """Prevent the device from keep running if HVACMode.OFF or update heater switch state if not HVACMode.OFF."""
        if self._attr_hvac_mode == HVACMode.OFF:
            if self._is_device_active:
                _LOGGER.warning(
                    (
                        "The climate mode is OFF, but the switch device is ON. Turning off"
                        " device %s"
                    ),
                    self.heater_entity_id,
                )
                await self._async_heater_turn_off()
        else:
            await self._async_control_heating(force=True)
            self.async_write_ha_state()

    @callback
    def _async_switch_changed(self, event: Event[EventStateChangedData]) -> None:
        """Handle heater switch state changes."""
        new_state = event.data["new_state"]
        old_state = event.data["old_state"]
        if new_state is None:
            return
        if old_state is None:
            self.hass.async_create_task(
                self._check_switch_initial_state(), eager_start=True
            )
        self.async_write_ha_state()

    @callback
    def _async_update_temp(self, state: State) -> None:
        """Update thermostat with latest state from sensor."""
        try:
            cur_temp = float(state.state)
            if not math.isfinite(cur_temp):
                raise ValueError(f"Sensor has illegal state {state.state}")  # noqa: TRY301
            self._attr_current_temperature = cur_temp
        except ValueError as ex:
            _LOGGER.error("Unable to update from sensor: %s", ex)

    async def _async_control_heating(
        self, time: datetime | None = None, force: bool = False
    ) -> None:
        """Check if we need to turn heating on or off."""
        async with self._temp_lock:
            if not self._active and None not in (
                self._attr_current_temperature,
                self._attr_target_temperature,
            ):
                self._active = True
                _LOGGER.debug(
                    (
                        "Obtained current and target temperature. "
                        "General thermostat active. %s, %s"
                    ),
                    self._attr_current_temperature,
                    self._attr_target_temperature,
                )

            if not self._active or self._attr_hvac_mode == HVACMode.OFF:
                return

            # If the `force` argument is True, we
            # ignore `min_cycle_duration`.
            # If the `time` argument is not none, we were invoked for
            # keep-alive purposes, and `min_cycle_duration` is irrelevant.
            if not force and time is None and self.min_cycle_duration:
                if self._is_device_active:
                    current_state = STATE_ON
                else:
                    current_state = HVACMode.OFF
                try:
                    long_enough = condition.state(
                        self.hass,
                        self.heater_entity_id,
                        current_state,
                        self.min_cycle_duration,
                    )
                except ConditionError:
                    long_enough = False

                if not long_enough:
                    return

            assert self._attr_current_temperature is not None and self._attr_target_temperature is not None
            too_cold = self._attr_target_temperature >= self._attr_current_temperature + self._attr_cold_tolerance
            too_hot = self._attr_current_temperature >= self._attr_target_temperature + self._attr_hot_tolerance
            if self._is_device_active:
                if (self.ac_mode and too_cold) or (not self.ac_mode and too_hot):
                    _LOGGER.debug("Turning off heater %s", self.heater_entity_id)
                    await self._async_heater_turn_off()
                elif time is not None:
                    # The time argument is passed only in keep-alive case
                    _LOGGER.debug(
                        "Keep-alive - Turning on heater heater %s",
                        self.heater_entity_id,
                    )
                    await self._async_heater_turn_on()
            else:
                if (self.ac_mode and too_hot) or (not self.ac_mode and too_cold):
                    _LOGGER.debug("Turning on heater %s", self.heater_entity_id)
                    await self._async_heater_turn_on()
                elif time is not None:
                    # The time argument is passed only in keep-alive case
                    _LOGGER.debug(
                        "Keep-alive - Turning off heater %s", self.heater_entity_id
                    )
                    await self._async_heater_turn_off()

    @property
    def _is_device_active(self) -> bool | None:
        """If the toggleable device is currently active."""
        if not self.hass.states.get(self.heater_entity_id):
            return None

        return self.hass.states.is_state(self.heater_entity_id, STATE_ON)

    async def _async_heater_turn_on(self) -> None:
        """Turn heater toggleable device on."""
        data = {ATTR_ENTITY_ID: self.heater_entity_id}
        await self.hass.services.async_call(
            HOMEASSISTANT_DOMAIN, SERVICE_TURN_ON, data, context=self._context
        )

    async def _async_heater_turn_off(self) -> None:
        """Turn heater toggleable device off."""
        data = {ATTR_ENTITY_ID: self.heater_entity_id}
        await self.hass.services.async_call(
            HOMEASSISTANT_DOMAIN, SERVICE_TURN_OFF, data, context=self._context
        )

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        if preset_mode not in (self.preset_modes or []):
            raise ValueError(
                f"Got unsupported preset_mode {preset_mode}. Must be one of"
                f" {self.preset_modes}"
            )
        if preset_mode == self._attr_preset_mode:
            # I don't think we need to call async_write_ha_state if we didn't change the state
            return

        self._attr_preset_mode = preset_mode
        self._attr_target_temperature = self._attr_preset_temperatures[self._attr_preset_modes.index(self._attr_preset_mode)]
        if preset_mode == PRESET_NONE:
            self._set_attr_preset_mode_based_on_target_temp()
        elif preset_mode not in self._attr_auto_update_preset_modes:
            self._set_attr_preset_temperatures(PRESET_NONE, self._attr_target_temperature)
        await self._async_control_heating(force=True)
        self.async_write_ha_state()

    @final
    async def async_handle_set_preset_temperature_service(self, preset_mode: str, temperature: float) -> None:
        """Validate and set new preset temperature."""
        self._valid_mode_or_raise("preset", preset_mode, self.preset_modes)
        min_temp = self.min_temp
        max_temp = self.max_temp
        if temperature < min_temp or temperature > max_temp:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="temp_out_of_range",
                translation_placeholders={
                    "check_temp": str(temperature),
                    "min_temp": str(min_temp),
                    "max_temp": str(max_temp),
                },
            )
        await self.async_set_preset_temperature(preset_mode, temperature)

    async def async_set_preset_temperature(self, preset_mode: str, temperature: float) -> None:
        """Set new preset temperature."""
        if (self._attr_preset_mode != PRESET_NONE
            and self._attr_preset_mode in self._attr_auto_update_preset_modes
        ):
            if preset_mode == self._attr_preset_mode:
                await self.async_set_temperature(temperature=temperature)
            else:
                self._set_attr_preset_temperatures(preset_mode, temperature)
                self.async_write_ha_state()
        else:
            if preset_mode == PRESET_NONE:
                await self.async_set_temperature(temperature=temperature)
            elif preset_mode == self._attr_preset_mode:
                self._set_attr_preset_temperatures(preset_mode, temperature)
                await self.async_set_temperature(temperature=temperature)
            else:
                self._set_attr_preset_temperatures(preset_mode, temperature)
                self._set_attr_preset_mode_based_on_target_temp()
                self.async_write_ha_state()

    @final
    async def async_handle_reset_preset_temperature_service(self, preset_mode: str | None = None) -> None:
        """Validate and reset preset temperature."""
        if preset_mode:
            self._valid_mode_or_raise("preset", preset_mode, self._presets.keys())
        await self.async_reset_preset_temperature(preset_mode)

    async def async_reset_preset_temperature(self, preset_mode: str | None) -> None:
        """Reset preset temperature."""
        if preset_mode:
            await self.async_set_preset_temperature(preset_mode, self._presets[preset_mode])
        else:
            self._attr_preset_temperatures = [self._attr_preset_temperatures[0], *self._presets.values()]
            if self._attr_preset_mode != PRESET_NONE:
                await self.async_set_temperature(temperature=self._presets[self._attr_preset_mode])
            else:
                self._set_attr_preset_mode_based_on_target_temp()
                self.async_write_ha_state()

    @final
    async def async_handle_set_tolerance_service(self, cold_tolerance: float | None = None, hot_tolerance: float | None = None) -> None:
        """Set cold and hot tolerance."""
        await self.async_set_tolerance(cold_tolerance, hot_tolerance)

    async def async_set_tolerance(self, cold_tolerance: float | None = None, hot_tolerance: float | None = None) -> None:
        """Set cold and hot tolerance."""
        if cold_tolerance is not None:
            self._attr_cold_tolerance = abs(cold_tolerance)
        if hot_tolerance is not None:
            self._attr_hot_tolerance = abs(hot_tolerance)
        if (cold_tolerance is not None
            or hot_tolerance is not None
        ):
            await self._async_control_heating(force=True)
            self.async_write_ha_state()
