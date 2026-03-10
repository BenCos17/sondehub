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
| `min_publish_interval` | `10` | Minimum time in seconds between updates for the same radiosonde. Increase to reduce MQTT traffic. |
| `max_active_sondes` | `20` | Maximum number of active radiosondes to track simultaneously. Prevents unlimited device creation. |
| `sonde_timeout_minutes` | `30` | Minutes of silence before a radiosonde is automatically removed from tracking. |
| `announce_all_entities` | `false` | Set to `true` to create all telemetry entities (latitude, longitude, speed, heading, etc.). Default (false) creates only essential entities (altitude, temperature, humidity, battery) plus status and location. |
| `area_alert_enabled` | `false` | Enable area/geofence alerts. |
| `area_lat_min` | `-90` | Minimum latitude of alert area. |
| `area_lat_max` | `90` | Maximum latitude of alert area. |
| `area_lon_min` | `-180` | Minimum longitude of alert area. |
| `area_lon_max` | `180` | Maximum longitude of alert area. |
| `amateur` | `false` | Set to `true` to also receive amateur high-altitude balloon launches. |
| `filter_serials` | _(empty)_ | List of specific radiosonde serial numbers to track (e.g. `R3320848`). Leave empty to receive **all** radiosondes globally. |

### Device & Entity Structure (v1.1.0+)

#### SondeHub Addon Device

The main addon device contains:

- **Active Radiosondes** (Sensor): Count of actively tracked radiosondes with full live telemetry of each sonde (altitude, temperature, humidity, location, battery, etc.) as attributes
- **Latest Radiosonde** (Sensor): Serial of the most recently received radiosonde
- **Any Radiosonde In Alert Area** (Binary Sensor): On/Off indicator if any sonde is in the configured geofence
- **Last Radiosonde In Alert Area** (Sensor): Serial of the last sonde to enter the alert area with its location data

#### Per-Radiosonde Device

For each active radiosonde, a separate device is created with:

**Main Sensors** (always created):
- **Altitude** (m) - Distance above ground level
- **Temperature** (°C) - Atmospheric temperature
- **Humidity** (%) - Relative humidity
- **Battery** (%) - Radiosonde battery level
- **Status** (Diagnostic) - "receiving" status with type, uploader, and last_seen attributes
- **Location** (Device Tracker) - GPS position with lat/lon/altitude in attributes

**Additional Sensors** (if `announce_all_entities: true`):
- Latitude / Longitude (Diagnostic)
- Horizontal Speed / Vertical Speed (m/s, Diagnostic)
- Heading (°, Diagnostic)
- Satellites (count, Diagnostic)
- Frequency (MHz, Diagnostic)
- RSSI (dBm signal strength, Diagnostic)
- Frame (count, Diagnostic)

All entities are properly tagged with:
- Device class (temperature, humidity, distance, speed, etc.)
- Unit of measurement
- Icons for quick visual identification
- Entity categories (diagnostic entities hidden by default in HA UI)

### Auto-Cleanup & Capacity Management

**Problem**: If many radiosondes pass overhead throughout the day, you could end up with hundreds of devices cluttering Home Assistant.

**Solution**:
- Radiosondes are automatically **removed** if not heard from for `sonde_timeout_minutes` (default: 30 minutes)
- If you exceed `max_active_sondes` (default: 20), new sondes are ignored until room opens up
- The **Active Radiosondes** sensor shows current count vs. max capacity
- Logs indicate when devices are added/removed

**Example scenario**:
- 50 radiosondes pass overhead during the day
- Only 20 devices are created (max_active_sondes limit)
- After 30 minutes of silence, unused sondes are purged
- New ones auto-populate as others expire
- Device list stays manageable

### Tips

- Radiosondes are launched twice daily from weather stations worldwide. New devices will appear automatically when a sonde is picked up by a receiver near you.
- Use `filter_serials` if you only want to track a known sonde to reduce MQTT traffic.
- Increase `min_publish_interval` to reduce MQTT message load (e.g., 30-60 seconds).
- Set `announce_all_entities: true` if you want detailed telemetry (speed, heading, etc.) for dashboards/automations.
- The SondeHub data is crowd-sourced. Coverage depends on the global network of volunteer receivers.

### Automations Example

#### Alert when a sonde enters your area

```yaml
automation:
  - alias: "Radiosonde Alert"
    trigger:
      platform: state
      entity_id: binary_sensor.any_radiosonde_in_alert_area
      to: "on"
    action:
      service: notify.notify
      data:
        message: "🎈 Radiosonde detected in alert area: {{ state_attr('sensor.last_radiosonde_in_alert_area', 'attributes') }}"
```

#### Log when new radiosondes appear

```yaml
automation:
  - alias: "Log New Radiosondes"
    trigger:
      platform: template
      value_template: "{{ state_attr('sensor.active_radiosondes', 'radiosondes') | length > 0 }}"
    action:
      service: system_log.write
      data:
        message: "{{ state_attr('sensor.active_radiosondes', 'radiosondes') | tojson }}"
        level: info
```

### Data License

Radiosonde data is provided by [SondeHub](https://sondehub.org) under the
[Creative Commons BY-SA 2.0](https://creativecommons.org/licenses/by-sa/2.0/) license.
