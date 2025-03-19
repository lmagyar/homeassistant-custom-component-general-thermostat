"""Adds support for general thermostat units' modifiable attributes."""

from __future__ import annotations

import logging

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
# from homeassistant.const import UnitOfTemperature
from homeassistant.core import (
    CoreState,
    Event,
    EventStateChangedData,
    HomeAssistant,
    State,
    callback,
)
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from homeassistant.const import (
    ATTR_ASSUMED_STATE,
    ATTR_ATTRIBUTION,
    ATTR_DEVICE_CLASS,
    ATTR_ENTITY_PICTURE,
    ATTR_FRIENDLY_NAME,
    ATTR_ICON,
    ATTR_SUPPORTED_FEATURES,
    ATTR_UNIT_OF_MEASUREMENT,
    DEVICE_DEFAULT_NAME,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    EntityCategory,
    ATTR_ENTITY_ID,
    EVENT_HOMEASSISTANT_START,
)

from homeassistant.helpers.event import (
    async_track_state_change_event,
)
from homeassistant.components.climate.const import (
    ATTR_MAX_TEMP,
    ATTR_MIN_TEMP,
    ATTR_PRESET_MODES,
    ATTR_TARGET_TEMP_STEP,
)

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class GeneralThermostatNumber(NumberEntity):
    """Representation of a general_thermostat attribute entity."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_should_poll = False

    def __init__(
        self,
        hass: HomeAssistant,
        unique_id: str | None,
        name: str,
        icon: str | None,

        unit_of_measurement: str | None,

        climate_entity_id: str,
        climate_entity_attr: str,
        climate_entity_attr_index_attr: str,
        climate_entity_attr_index_value: str,
        climate_entity_service: str,
        climate_entity_service_data_consts: dict,
        climate_entity_service_data_field: str,


    ) -> None:
        """Initialize the Demo Number entity."""

        self._attr_unique_id = unique_id
        self._attr_name = name
        self._attr_icon = icon

        if unit_of_measurement is not None:
            self._attr_native_unit_of_measurement = unit_of_measurement

        self._climate_entity_id = climate_entity_id
        self._climate_entity_attr = climate_entity_attr
        self._climate_entity_attr_index_attr = climate_entity_attr_index_attr
        self._climate_entity_attr_index_value = climate_entity_attr_index_value
        self._climate_entity_service = climate_entity_service
        self._climate_entity_service_data_consts = climate_entity_service_data_consts
        self._climate_entity_service_data_field = climate_entity_service_data_field

        # self._attr_device_info = async_device_info_to_link_from_entity(
        #     hass,
        #     heater_entity_id,
        # )
        # self._attr_device_info = DeviceInfo(
        #     identifiers={
        #         # Serial numbers are unique identifiers within a specific domain
        #         (DOMAIN, unique_id)
        #     },
        #     name=device_name,
        # )

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added."""
        await super().async_added_to_hass()

        # Add listener
        self.async_on_remove(
            async_track_state_change_event(
                self.hass, [self._climate_entity_id], self._async_climate_changed
            )
        )

        @callback
        def _async_startup(_: Event | None = None) -> None:
            """Init on startup."""
            climate_state = self.hass.states.get(self._climate_entity_id)
            if climate_state and climate_state.state not in (
                STATE_UNAVAILABLE,
                STATE_UNKNOWN,
            ):

                self._attr_native_max_value = climate_state.attributes[ATTR_MAX_TEMP]
                self._attr_native_min_value = climate_state.attributes[ATTR_MIN_TEMP]
                self._attr_native_step = climate_state.attributes[ATTR_TARGET_TEMP_STEP]
            self._async_update_value(None, climate_state)

        if self.hass.state is CoreState.running:
            _async_startup()
        else:
            self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_START, _async_startup)

    async def _async_climate_changed(self, event: Event[EventStateChangedData]) -> None:
        old_state = event.data["old_state"]
        new_state = event.data["new_state"]
        self._async_update_value(old_state, new_state)

    def _async_update_value(self, old_state: State | None, new_state: State | None) -> None:
        if new_state is None or new_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            if self._attr_available:
                self._attr_available = False
                self.async_write_ha_state() ###TODO kell ez?
        else:
            should_write_state = False
            if not self._attr_available:
                self._attr_available = True
                should_write_state = True
            attribute_index = new_state.attributes[self._climate_entity_attr_index_attr].index(self._climate_entity_attr_index_value)
            new_attribute = new_state.attributes[self._climate_entity_attr][attribute_index]
            if old_state is None or (old_attribute_list := old_state.attributes[self._climate_entity_attr]) is None or old_attribute_list[attribute_index] != new_attribute:
                self._attr_native_value = float(new_attribute)
                should_write_state = True
            if should_write_state:
                self.async_write_ha_state() ###TODO kell ez?

    async def async_set_native_value(self, value: float) -> None:
        await self.hass.services.async_call(
            DOMAIN,
            self._climate_entity_service,
            {
                ATTR_ENTITY_ID: self.state.entity_id,
                **self._climate_entity_service_data_consts,
                self._climate_entity_service_data_field: value,
            },
        )
