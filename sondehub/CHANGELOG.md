# Changelog
## 1.0.11
- Fix `Last Radiosonde In Alert Area` initial state to avoid `unknown` after startup.
- Publish retained default payload to `sondehub/alerts/last_in_area` on startup.
- Publish retained updates for `sondehub/alerts/last_in_area` when a sonde enters the alert area.

## 1.0.10
- Fix Home Assistant MQTT discovery topic layout for per-radiosonde entities so sensors/device tracker are created reliably.
- Add cleanup for retained discovery topics from the previous broken topic format.
- Add missing add-on config schema keys for `max_active_sondes`, `sonde_timeout_minutes`, and `announce_all_entities`.

## 1.0.9
- **[BREAKING] Complete device/entity restructure for better Home Assistant integration**:
  - Each radiosonde now gets an individual device (grouped under SondeHub addon)
  - Individual sensor entities per telemetry field (Temperature, Humidity, Altitude, Battery, etc.)
  - Proper device classes and units for each sensor (temperature in °C, altitude in m, etc.)
  - Diagnostic entities hidden by default to keep UI clean
  - Location entity with GPS attributes for each sonde
- Add **Auto-cleanup**: Radiosondes automatically removed after 30 minutes of silence (configurable)
- Add **Max active sondes limit**: Prevent unlimited device creation if many sondes pass overhead (default: 20)
- Add **Active Radiosondes overview**: Sensor on addon showing count and live data of all tracked sondes
- Add configuration options: `max_active_sondes`, `sonde_timeout_minutes`, `announce_all_entities`
- **Migration note**: Delete old devices manually after updating as the structure has changed significantly

## 1.0.8
- Fix add-on schema parsing for area alert bounds to ensure add-on appears in the Home Assistant store.

## 1.0.7
- Add configurable geofence area alerts using latitude/longitude min/max bounds.
- Add global automation entities: `Any Radiosonde In Alert Area` and `Last Radiosonde In Alert Area`.
- Keep per-sonde summary entities while supporting unknown serial IDs ahead of time.

## 1.0.6
- Add per-sonde publish rate limiting with new `min_publish_interval` option.
- Change discovery model to one summary sensor per sonde with full telemetry in attributes.
- Remove legacy retained per-field discovery entities from previous versions.

## 1.0.4
- Remove MQTT device tracker discovery to avoid Away/Unknown-only entities.
- Keep MQTT sensor discovery focused on telemetry entities.
- Improve cleanup of old retained tracker discovery topics.

## 1.0.3
- fix type just now also
- Group sensors under one device but seperate entities as it was causing issues in 1.0.1 

## 1.0.0

- Initial release
- Live streaming of radiosonde telemetry from SondeHub via MQTT
- HA MQTT Discovery: sensors for altitude, temperature, humidity, lat/lon, speed, heading, satellites, battery, frequency, RSSI, and frame number
- Device tracker for map view
- Optional amateur balloon feed
- Optional filtering by serial number
