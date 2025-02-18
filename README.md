
# General Thermostat

This is a fork of the official [`generic_thermostat`](https://www.home-assistant.io/integrations/generic_thermostat/) component/integration reverting breaking changes:

- [Auto select thermostat preset when selecting temperature #134146](https://github.com/home-assistant/core/pull/134146)

## How to use

- Replace all `platform: generic_thermostat` with `platform: general_thermostat`
- Restart Home Assistant
