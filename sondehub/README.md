# Home Assistant Add-on: SondeHub

Stream live radiosonde (weather balloon) telemetry from [SondeHub](https://sondehub.org)
directly into Home Assistant via MQTT.

## Features

- Streams live radiosonde telemetry from the global SondeHub network
- Automatically creates HA sensors (altitude, temperature, humidity, GPS, speed, etc.) via MQTT Discovery
- Creates a device tracker so each sonde appears on the Home Assistant map
- Optional filtering by specific serial numbers
- Optional amateur high-altitude balloon feed

Uses the official [sondehub Python SDK](https://pypi.org/project/sondehub/).

## Installation

Add this repository to Home Assistant and install the **SondeHub** add-on.

See [DOCS.md](DOCS.md) for full configuration instructions.
