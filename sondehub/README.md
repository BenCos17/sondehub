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

[![Add repository to Home Assistant](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2FBenCos17%2Fsondehub)

Or manually add `https://github.com/BenCos17/sondehub` in Home Assistant → Settings → Add-ons → Add-on Store → ⋮ → Repositories, then install the **SondeHub** add-on.

See [DOCS.md](DOCS.md) for full configuration instructions.
