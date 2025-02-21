
# General Thermostat

This is a fork of the official Home Assistant [`generic_thermostat`](https://www.home-assistant.io/integrations/generic_thermostat/) component/integration:

- Remember changed preset temps over restarts (store them in state attribute)
- Remember changed preset temps like remembering non-preset temp
- Bugfix: After restart in preset mode don't restore wrong target temp when going back to none preset
- Bugfix: After restart recalculate the switch state, because sensor temperature maybe changed as much during restart that it requires it (a restart can be caused by a longer power outage also)
- Reverting breaking changes introduced in 2025.2 [Auto select thermostat preset when selecting temperature #134146](https://github.com/home-assistant/core/pull/134146)

## Installation

1. Navigate in your Home Assistant frontend to **HACS**
1. In the **...** menu at the top right corner click **Custom repositories**,
   add
   `https://github.com/lmagyar/homeassistant-custom-component-general-thermostat`
   as `Integration`.
1. Find the "General Thermostat" integration and click it.
1. Click on the "DOWNLOAD" button.

## How to use

- Replace all `platform: generic_thermostat` with `platform: general_thermostat` in your .yaml files
- Restart Home Assistant
