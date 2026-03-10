# Home Assistant Add-on: SondeHub

## How to use

### Prerequisites

1. Install and configure the **Mosquitto MQTT** add-on (or any MQTT broker).
2. Enable the **MQTT integration** in Home Assistant Settings → Devices & Services.

### Configuration

| Option | Default | Description |
|---|---|---|
| `mqtt_host` | `core-mosquitto` | Hostname of your MQTT broker. Use `core-mosquitto` for the built-in Mosquitto add-on. |
| `mqtt_port` | `1883` | MQTT broker port. |
| `mqtt_user` | _(blank)_ | MQTT username (if required). |
| `mqtt_password` | _(blank)_ | MQTT password (if required). |
| `amateur` | `false` | Set to `true` to also receive amateur high-altitude balloon launches. |
| `filter_serials` | _(empty)_ | List of specific radiosonde serial numbers to track (e.g. `R3320848`). Leave empty to receive **all** radiosondes globally. |

### What gets created in Home Assistant

For each radiosonde detected, the add-on automatically creates (via MQTT Discovery):

- **Sensors**: Altitude, Temperature, Humidity, Latitude, Longitude, Horizontal Speed, Vertical Speed, Heading, GPS Satellites, Battery Voltage, Frequency, Frame Number, RSSI
- **Device Tracker**: Shows the radiosonde position on the Home Assistant map

All entities are grouped under a single **device** named `Radiosonde <serial>`.

### Tips

- Radiosondes are launched twice daily from weather stations worldwide. New devices will appear automatically when a sonde is picked up by a receiver near you.
- Use `filter_serials` if you only want to track a known sonde to reduce MQTT traffic.
- The SondeHub data is crowd-sourced. Coverage depends on the global network of volunteer receivers.

### Data License

Radiosonde data is provided by [SondeHub](https://sondehub.org) under the
[Creative Commons BY-SA 2.0](https://creativecommons.org/licenses/by-sa/2.0/) license.
