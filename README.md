
# General Thermostat

This is a fork of the official Home Assistant [`generic_thermostat`](https://www.home-assistant.io/integrations/generic_thermostat/) component/integration:

- New service/action to change preset temperature even when the thermostat is not in that specific preset
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

## Services

### general_thermostat.set_preset_temperature

```
action: general_thermostat.set_preset_temperature
target:
  entity_id: climate.living_room_thermostat
data:
  preset_mode: away
  temperature: 17
```

## Extras

Full blown demo (with dummy temperature sensor and dummy thermostat switch):
- Read-only sensors for the preset temperatures
- Number entities for preset manipulation, even when the thermostat is not in that preset

![Screenshot](https://github.com/lmagyar/homeassistant-custom-component-general-thermostat/raw/main/res/screenshot.png)

### Configuration

```
climate:
  - platform: general_thermostat
    name: Demo Living room Thermostat
    heater: input_boolean.demo_living_room_thermostat_switch
    target_sensor: sensor.demo_living_room_temperature
    min_temp: 15
    max_temp: 25
    target_temp_step: 0.5
    ac_mode: false
    cold_tolerance: 0.1
    hot_tolerance: 0.1
    away_temp: 18
    precision: 0.1

input_boolean:

  # Just a dummy fake switch for demonstration
  demo_living_room_thermostat_switch:
    name: Living room Thermostat switch
    icon: mdi:sofa
    initial: false

template:

  - sensor:

    # Just a dummy fake sensor for demonstration
    - name: "Demo Living room temperature"
      state: 22
      state_class: measurement
      unit_of_measurement: '°C'
      device_class: temperature

    # Read-only sensor for none preset temperature
    - name: "Demo Living room normal target temperature"
      state: '{{ state_attr("climate.demo_living_room_thermostat", "preset_temperatures")[state_attr("climate.demo_living_room_thermostat", "preset_modes").index("none")] }}'
      state_class: measurement
      unit_of_measurement: '°C'
      device_class: temperature

    # Read-only sensor for away preset temperature
    - name: "Demo Living room away target temperature"
      state: '{{ state_attr("climate.demo_living_room_thermostat", "preset_temperatures")[state_attr("climate.demo_living_room_thermostat", "preset_modes").index("away")] }}'
      state_class: measurement
      unit_of_measurement: '°C'
      device_class: temperature

  - number:

    # Number entity for none preset manipulation, even when the thermostat is not in none preset
    - name: "Demo Living room normal target temperature"
      min: '{{ state_attr("climate.demo_living_room_thermostat", "min_temp") | float(default=15) }}'
      max: '{{ state_attr("climate.demo_living_room_thermostat", "max_temp") | float(default=25) }}'
      step: '{{ state_attr("climate.demo_living_room_thermostat", "target_temp_step") | float(default=0.5) }}'
      unit_of_measurement: '°C'
      icon: 'mdi:thermometer'
      state: '{{ state_attr("climate.demo_living_room_thermostat", "preset_temperatures")[state_attr("climate.demo_living_room_thermostat", "preset_modes").index("none")] }}'
      set_value :
        - action: general_thermostat.set_preset_temperature
          target:
            entity_id: climate.demo_living_room_thermostat
          data:
            preset_mode: none
            temperature: '{{ value }}'

    # Number entity for away preset manipulation, even when the thermostat is not in away preset
    - name: "Demo Living room away target temperature"
      min: '{{ state_attr("climate.demo_living_room_thermostat", "min_temp") | float(default=15) }}'
      max: '{{ state_attr("climate.demo_living_room_thermostat", "max_temp") | float(default=25) }}'
      step: '{{ state_attr("climate.demo_living_room_thermostat", "target_temp_step") | float(default=0.5) }}'
      unit_of_measurement: '°C'
      icon: 'mdi:thermometer'
      state: '{{ state_attr("climate.demo_living_room_thermostat", "preset_temperatures")[state_attr("climate.demo_living_room_thermostat", "preset_modes").index("away")] }}'
      set_value :
        - action: general_thermostat.set_preset_temperature
          target:
            entity_id: climate.demo_living_room_thermostat
          data:
            preset_mode: away
            temperature: '{{ value }}'
```

### Dashboard section

```
type: grid
cards:
  - type: entities
    entities:
      - entity: sensor.demo_living_room_temperature
      - entity: input_boolean.demo_living_room_thermostat_switch
  - type: thermostat
    entity: climate.demo_living_room_thermostat
    show_current_as_primary: true
    features:
      - style: icons
        type: climate-preset-modes
  - type: entities
    entities:
      - entity: sensor.demo_living_room_normal_target_temperature
      - entity: sensor.demo_living_room_away_target_temperature
      - entity: number.demo_living_room_normal_target_temperature
      - entity: number.demo_living_room_away_target_temperature
```
