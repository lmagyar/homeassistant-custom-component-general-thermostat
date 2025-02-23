
# General Thermostat

This is a fork of the official Home Assistant [`generic_thermostat`](https://www.home-assistant.io/integrations/generic_thermostat/) component/integration:

- Remember changed preset temps over restarts (store them in state attribute `preset_temperatures`)
  - Note: Due to a bug in the UI, Developer tools / States / Attributes column doesn't refresh automatically this attribute, because this is not a plain string attribute, but a list of strings, so you have to refresh the page to see the changes
- Remember changed preset temps like remembering non-preset temp
- Bugfix: After restart in preset mode don't restore wrong target temp when going back to none preset
- Bugfix: After restart recalculate the switch state, because sensor temperature maybe changed as much during restart that it requires it (a restart can be caused by a longer power outage also)
- Reverting breaking changes introduced in 2025.2 [Auto select thermostat preset when selecting temperature #134146](https://github.com/home-assistant/core/pull/134146)

## Installation

1. Navigate in your Home Assistant frontend to **HACS** (if you don't have HACS, see how to install it: https://www.hacs.xyz/docs/use/)
1. In the **...** menu at the top right corner click **Custom repositories**,
   add
   `https://github.com/lmagyar/homeassistant-custom-component-general-thermostat`
   as `Integration`.
1. Find the "General Thermostat" integration and click it.
1. Click on the "DOWNLOAD" button.
1. Restart Home Assistant

## How to use

- Replace all `platform: generic_thermostat` with `platform: general_thermostat` in your .yaml files - Note the change from gener**IC** to gener**AL**
  - Remove: `target_temp: xx` lines
  - Do not remove: `away_temp: xx` or any other currently used preset temps, these are required to enable these presets, but these values will be used only on the first ever startup, later the saved values will be used
- Restart Home Assistant

**Note:** Currently you can change preset temperatures only by selecting that preset and changing the target temperature. I'm planning to add a new `set_preset_temperature` service.

## Extras

You can create sensors to show the saved normal and preset temperatures:

```
template:

  - sensor:

      - name: "Living room normal target temperature"
        state: '{{ state_attr("climate.living_room_thermostat", "preset_temperatures")[state_attr("climate.living_room_thermostat", "preset_modes").index("none")] }}'
        state_class: measurement
        unit_of_measurement: '°C'
        device_class: temperature

      - name: "Living room away target temperature"
        state: '{{ state_attr("climate.living_room_thermostat", "preset_temperatures")[state_attr("climate.living_room_thermostat", "preset_modes").index("away")] }}'
        state_class: measurement
        unit_of_measurement: '°C'
        device_class: temperature
```
