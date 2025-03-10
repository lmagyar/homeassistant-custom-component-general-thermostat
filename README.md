
# General Thermostat

This is a fork of the official Home Assistant [`generic_thermostat`](https://www.home-assistant.io/integrations/generic_thermostat/) component/integration:

Changes:
- Preset temperatures can be changed
  - New service/action `general_thermostat.set_preset_temperature` added to change preset temperatures even when the thermostat is not in that specific preset
  - Remembers changed preset temperatures, even over restarts (stores them in state attribute `preset_temperatures`)

- Preset temperatures can be automatically updated by changing the target temperature (eg. on the dial)
  - New config option `auto_update_preset_modes` (also available as attribute)
  - Default all preset modes are included, to disable auto-update completely, set an empty value
  - Auto-updates the preset temperature when that particular preset is selected and is in the auto_update_preset_modes
  - This partially reverts breaking changes introduced in 2025.2 [Auto select thermostat preset when selecting temperature #134146](https://github.com/home-assistant/core/pull/134146) for auto_update_preset_modes

- Add new presets: `boost` (this is part of the climate integration), `reduce` (this is completely new)
- Add new icon for the `activity` and the new `reduce` presets (works on HA OS VM (when I tested), but doesn't work on any other installations, HA is unbelievably broken in it's each corner)

- Bugfixes in the original generic_thermostat code:
  - After restart recalculate the switch state, because sensor temperature maybe changed as much during restart that it requires it (because a restart can be caused by a longer power outage also)
  - After restart in preset mode don't restore wrong target temp when going back to none preset (original code stored the saved non-preset temperature only in memory)

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
  - Optionally set `auto_update_preset_modes:` to a shorter list than all specified preset modes
- Restart Home Assistant

**Note:** Each time you rename the thermostat entity, it will forget the settings, because they are stored in the state under the previous entity name. This is normal.

## Custom configuration variables

### auto_update_preset_modes (comma separated list)

List preset modes that's preset temperature should be automatically updated when that particular preset is selected.

## Custom services / actions

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
- `away` and `eco` preset modes' temperature are auto updated when these presets are selected
- `home` and `eco` preset modes' temperature can be changed only by calling the `general_thermostat.set_preset_temperature` service / action (they behave like the official generic_thermostat)
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
    ac_mode: false
    min_temp: 10
    max_temp: 25
    target_temp_step: 0.5
    precision: 0.1
    cold_tolerance: 0.1
    hot_tolerance: 0.1
    home_temp: 22
    sleep_temp: 20
    eco_temp: 16
    away_temp: 10
    auto_update_preset_modes: away, eco

input_boolean:

  # Just a dummy fake switch for demonstration
  demo_living_room_thermostat_switch:
    name: Demo Living room Thermostat switch
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
      availability: '{{ states("climate.demo_living_room_thermostat") is not match("un\w*") }}'

    # Read-only sensor for home preset temperature
    - name: "Demo Living room home target temperature"
      state: '{{ state_attr("climate.demo_living_room_thermostat", "preset_temperatures")[state_attr("climate.demo_living_room_thermostat", "preset_modes").index("home")] }}'
      state_class: measurement
      unit_of_measurement: '°C'
      device_class: temperature
      availability: '{{ states("climate.demo_living_room_thermostat") is not match("un\w*") }}'

    # Read-only sensor for sleep preset temperature
    - name: "Demo Living room sleep target temperature"
      state: '{{ state_attr("climate.demo_living_room_thermostat", "preset_temperatures")[state_attr("climate.demo_living_room_thermostat", "preset_modes").index("sleep")] }}'
      state_class: measurement
      unit_of_measurement: '°C'
      device_class: temperature
      availability: '{{ states("climate.demo_living_room_thermostat") is not match("un\w*") }}'

    # Read-only sensor for eco preset temperature
    - name: "Demo Living room eco target temperature"
      state: '{{ state_attr("climate.demo_living_room_thermostat", "preset_temperatures")[state_attr("climate.demo_living_room_thermostat", "preset_modes").index("eco")] }}'
      state_class: measurement
      unit_of_measurement: '°C'
      device_class: temperature
      availability: '{{ states("climate.demo_living_room_thermostat") is not match("un\w*") }}'

    # Read-only sensor for away preset temperature
    - name: "Demo Living room away target temperature"
      state: '{{ state_attr("climate.demo_living_room_thermostat", "preset_temperatures")[state_attr("climate.demo_living_room_thermostat", "preset_modes").index("away")] }}'
      state_class: measurement
      unit_of_measurement: '°C'
      device_class: temperature
      availability: '{{ states("climate.demo_living_room_thermostat") is not match("un\w*") }}'

  - number:

    # Number entity for none preset manipulation, even when the thermostat is not in none preset
    - name: "Demo Living room normal target temperature"
      min: '{{ state_attr("climate.demo_living_room_thermostat", "min_temp") | float(default=10) }}'
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
      availability: '{{ states("climate.demo_living_room_thermostat") is not match("un\w*") }}'

    # Number entity for home preset manipulation, even when the thermostat is not in home preset
    - name: "Demo Living room home target temperature"
      min: '{{ state_attr("climate.demo_living_room_thermostat", "min_temp") | float(default=10) }}'
      max: '{{ state_attr("climate.demo_living_room_thermostat", "max_temp") | float(default=25) }}'
      step: '{{ state_attr("climate.demo_living_room_thermostat", "target_temp_step") | float(default=0.5) }}'
      unit_of_measurement: '°C'
      icon: 'mdi:thermometer'
      state: '{{ state_attr("climate.demo_living_room_thermostat", "preset_temperatures")[state_attr("climate.demo_living_room_thermostat", "preset_modes").index("home")] }}'
      set_value :
        - action: general_thermostat.set_preset_temperature
          target:
            entity_id: climate.demo_living_room_thermostat
          data:
            preset_mode: home
            temperature: '{{ value }}'
      availability: '{{ states("climate.demo_living_room_thermostat") is not match("un\w*") }}'

    # Number entity for sleep preset manipulation, even when the thermostat is not in sleep preset
    - name: "Demo Living room sleep target temperature"
      min: '{{ state_attr("climate.demo_living_room_thermostat", "min_temp") | float(default=10) }}'
      max: '{{ state_attr("climate.demo_living_room_thermostat", "max_temp") | float(default=25) }}'
      step: '{{ state_attr("climate.demo_living_room_thermostat", "target_temp_step") | float(default=0.5) }}'
      unit_of_measurement: '°C'
      icon: 'mdi:thermometer'
      state: '{{ state_attr("climate.demo_living_room_thermostat", "preset_temperatures")[state_attr("climate.demo_living_room_thermostat", "preset_modes").index("sleep")] }}'
      set_value :
        - action: general_thermostat.set_preset_temperature
          target:
            entity_id: climate.demo_living_room_thermostat
          data:
            preset_mode: sleep
            temperature: '{{ value }}'
      availability: '{{ states("climate.demo_living_room_thermostat") is not match("un\w*") }}'

    # Number entity for eco preset manipulation, even when the thermostat is not in eco preset
    - name: "Demo Living room eco target temperature"
      min: '{{ state_attr("climate.demo_living_room_thermostat", "min_temp") | float(default=10) }}'
      max: '{{ state_attr("climate.demo_living_room_thermostat", "max_temp") | float(default=25) }}'
      step: '{{ state_attr("climate.demo_living_room_thermostat", "target_temp_step") | float(default=0.5) }}'
      unit_of_measurement: '°C'
      icon: 'mdi:thermometer'
      state: '{{ state_attr("climate.demo_living_room_thermostat", "preset_temperatures")[state_attr("climate.demo_living_room_thermostat", "preset_modes").index("eco")] }}'
      set_value :
        - action: general_thermostat.set_preset_temperature
          target:
            entity_id: climate.demo_living_room_thermostat
          data:
            preset_mode: eco
            temperature: '{{ value }}'
      availability: '{{ states("climate.demo_living_room_thermostat") is not match("un\w*") }}'

    # Number entity for away preset manipulation, even when the thermostat is not in away preset
    - name: "Demo Living room away target temperature"
      min: '{{ state_attr("climate.demo_living_room_thermostat", "min_temp") | float(default=10) }}'
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
      availability: '{{ states("climate.demo_living_room_thermostat") is not match("un\w*") }}'
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
      - entity: sensor.demo_living_room_home_target_temperature
      - entity: sensor.demo_living_room_sleep_target_temperature
      - entity: sensor.demo_living_room_eco_target_temperature
      - entity: sensor.demo_living_room_away_target_temperature
      - entity: number.demo_living_room_normal_target_temperature
      - entity: number.demo_living_room_home_target_temperature
      - entity: number.demo_living_room_sleep_target_temperature
      - entity: number.demo_living_room_eco_target_temperature
      - entity: number.demo_living_room_away_target_temperature
```
