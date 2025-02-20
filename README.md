
# General Thermostat

This is a fork of the official Home Assistant [`generic_thermostat`](https://www.home-assistant.io/integrations/generic_thermostat/) component/integration:

- Reverting breaking changes introduced in 2025.2 [Auto select thermostat preset when selecting temperature #134146](https://github.com/home-assistant/core/pull/134146)
- Fixing: After reload recalculate the switch state, because sensor temperature maybe changed as much during restart that it requires it (a restart can be caused by a longer power outage also)
- Fixing: After reload in preset mode don't restore wrong target temp when going back to none preset
- Fixing: Remember changed preset temp like remembering non-preset temp

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
