# Changelog
## 1.0.6
- Add per-sonde publish rate limiting with new `min_publish_interval` option.
- Change discovery model to one summary sensor per sonde with full telemetry in attributes.
- Remove legacy retained per-field discovery entities from previous versions.

## 1.0.4
- Remove MQTT device tracker discovery to avoid Away/Unknown-only entities.
- Keep MQTT sensor discovery focused on telemetry entities.
- Improve cleanup of old retained tracker discovery topics.

## 1.0.3
-# fix type just now also
- Group sensors under one device but seperate entities as it was causing issues in 1.0.1 

## 1.0.0

- Initial release
- Live streaming of radiosonde telemetry from SondeHub via MQTT
- HA MQTT Discovery: sensors for altitude, temperature, humidity, lat/lon, speed, heading, satellites, battery, frequency, RSSI, and frame number
- Device tracker for map view
- Optional amateur balloon feed
- Optional filtering by serial number
