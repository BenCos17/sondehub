#!/usr/bin/env python3
"""SondeHub Home Assistant Add-on

Streams live radiosonde (weather balloon) telemetry from SondeHub to
Home Assistant via MQTT, using Home Assistant MQTT Discovery to
automatically create sensors and a device tracker for each radiosonde.

Uses the official sondehub Python SDK: https://pypi.org/project/sondehub/
"""

import json
import logging
import signal
import sys
import time

import paho.mqtt.client as mqtt
import sondehub as sondehub_lib

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("sondehub_addon")

OPTIONS_FILE = "/data/options.json"

# Mapping of SondeHub API field names to the state dict keys used above
FIELD_MAP = {
    "lat":      "latitude",
    "lon":      "longitude",
    "alt":      "altitude",
    "temp":     "temperature",
    "humidity": "humidity",
    "vel_h":    "speed_horizontal",
    "vel_v":    "speed_vertical",
    "heading":  "heading",
    "sats":     "satellites",
    "batt":     "battery",
    "freq":     "frequency",
    "frame":    "frame",
    "rssi":     "rssi",
}

# Values that sondehub uses to indicate "no data"
INVALID_VALUES = {None, "", "None", -9999, -9999.0}


def load_options() -> dict:
    with open(OPTIONS_FILE) as f:
        return json.load(f)


class SondeHubAddon:
    def __init__(self, opts: dict):
        self.mqtt_host: str = opts.get("mqtt_host", "core-mosquitto")
        self.mqtt_port: int = int(opts.get("mqtt_port", 1883))
        self.mqtt_user: str = opts.get("mqtt_user", "")
        self.mqtt_password: str = opts.get("mqtt_password", "")
        self.amateur: bool = opts.get("amateur", False)
        self.filter_serials: list = opts.get("filter_serials", [])
        self.min_publish_interval: int = max(0, int(opts.get("min_publish_interval", 10)))
        self.area_alert_enabled: bool = bool(opts.get("area_alert_enabled", False))
        self.area_lat_min: float = float(opts.get("area_lat_min", -90.0))
        self.area_lat_max: float = float(opts.get("area_lat_max", 90.0))
        self.area_lon_min: float = float(opts.get("area_lon_min", -180.0))
        self.area_lon_max: float = float(opts.get("area_lon_max", 180.0))

        self.announced: set = set()
        self.last_published: dict[str, float] = {}
        self.global_announced: bool = False
        self.sondes_in_area: set = set()
        self.mqtt_client: mqtt.Client | None = None
        self.stream = None
        
        # Single addon device shared by all sensors
        self.addon_device: dict = {
            "identifiers": ["sondehub_addon"],
            "name": "SondeHub",
            "model": "SondeHub Live Stream",
            "manufacturer": "ProjectHorus",
            "configuration_url": "https://github.com/bencos17/sondehub",
        }

    # ------------------------------------------------------------------
    # MQTT helpers
    # ------------------------------------------------------------------

    def _connect_mqtt(self) -> None:
        client = mqtt.Client(client_id="sondehub_ha_addon")
        client.on_connect = self._on_mqtt_connect
        client.on_disconnect = self._on_mqtt_disconnect
        if self.mqtt_user:
            client.username_pw_set(self.mqtt_user, self.mqtt_password)

        log.info("Connecting to MQTT broker %s:%d", self.mqtt_host, self.mqtt_port)
        client.connect(self.mqtt_host, self.mqtt_port, keepalive=60)
        client.loop_start()
        self.mqtt_client = client

    def _on_mqtt_connect(self, client, userdata, flags, rc) -> None:
        if rc == 0:
            log.info("Connected to MQTT broker")
        else:
            log.error("MQTT connection failed (rc=%d)", rc)

    def _on_mqtt_disconnect(self, client, userdata, rc) -> None:
        if rc != 0:
            log.warning("Unexpected MQTT disconnect (rc=%d)", rc)

    def _publish(self, topic: str, payload, retain: bool = False) -> None:
        if self.mqtt_client is None:
            return
        if isinstance(payload, dict):
            payload = json.dumps(payload)
        self.mqtt_client.publish(topic, payload, retain=retain)

    # ------------------------------------------------------------------
    # HA MQTT Discovery
    # ------------------------------------------------------------------

    def _is_in_alert_area(self, latitude: float, longitude: float) -> bool:
        return (
            self.area_lat_min <= latitude <= self.area_lat_max
            and self.area_lon_min <= longitude <= self.area_lon_max
        )

    def _announce_global_entities(self) -> None:
        """Publish MQTT Discovery config for global entities."""
        if self.global_announced:
            return

        latest_cfg: dict = {
            "name": "Latest Radiosonde",
            "unique_id": "sondehub_latest_radiosonde",
            "state_topic": "sondehub/latest/state",
            "value_template": "{{ value_json.serial | default('unknown') }}",
            "json_attributes_topic": "sondehub/latest/state",
            "availability_topic": "sondehub/global/availability",
            "icon": "mdi:radar",
            "device": self.addon_device,
        }
        self._publish("homeassistant/sensor/sondehub/latest_radiosonde/config", latest_cfg, retain=True)

        area_cfg: dict = {
            "name": "Any Radiosonde In Alert Area",
            "unique_id": "sondehub_any_in_alert_area",
            "state_topic": "sondehub/alerts/in_area",
            "payload_on": "ON",
            "payload_off": "OFF",
            "availability_topic": "sondehub/global/availability",
            "device_class": "occupancy",
            "icon": "mdi:map-marker-alert",
            "device": self.addon_device,
        }
        self._publish("homeassistant/binary_sensor/sondehub/any_in_alert_area/config", area_cfg, retain=True)

        last_area_cfg: dict = {
            "name": "Last Radiosonde In Alert Area",
            "unique_id": "sondehub_last_in_alert_area",
            "state_topic": "sondehub/alerts/last_in_area",
            "value_template": "{{ value_json.serial | default('none') }}",
            "json_attributes_topic": "sondehub/alerts/last_in_area",
            "availability_topic": "sondehub/global/availability",
            "icon": "mdi:crosshairs-gps",
            "device": self.addon_device,
        }
        self._publish("homeassistant/sensor/sondehub/last_in_alert_area/config", last_area_cfg, retain=True)

        self.global_announced = True

    def _announce_sonde(self, serial: str, payload: dict) -> None:
        """Publish MQTT Discovery config for a newly seen radiosonde."""
        safe = serial.replace("-", "_").replace(" ", "_").lower()
        state_topic = f"sondehub/{safe}/state"

        # Remove old retained discovery entities from previous addon versions.
        self._publish(f"homeassistant/device_tracker/sondehub/{safe}/config", "", retain=True)

        for legacy_field in set(FIELD_MAP.values()):
            self._publish(f"homeassistant/sensor/sondehub/{safe}_{legacy_field}/config", "", retain=True)
            self._publish(f"homeassistant/sensor/sondehub/{safe}/{legacy_field}/config", "", retain=True)

        cfg: dict = {
            "name": f"Radiosonde {serial}",
            "unique_id": f"sondehub_{safe}_summary",
            "state_topic": state_topic,
            "value_template": "{{ value_json.last_seen | default('unknown') }}",
            "json_attributes_topic": state_topic,
            "availability_topic": f"sondehub/{safe}/availability",
            "icon": "mdi:weather-windy",
            "device": self.addon_device,
        }
        self._publish(f"homeassistant/sensor/sondehub/{safe}_summary/config", cfg, retain=True)

        # Mark sonde as online
        self._publish(f"sondehub/{safe}/availability", "online", retain=True)

        log.info("Announced new radiosonde: %s", serial)
        self.announced.add(serial)

    # ------------------------------------------------------------------
    # SondeHub stream callback
    # ------------------------------------------------------------------

    def _on_sonde_message(self, message: dict) -> None:
        serial: str = message.get("serial", "unknown")
        safe: str = serial.replace("-", "_").replace(" ", "_").lower()

        if serial not in self.announced:
            self._announce_sonde(serial, message)

        state: dict = {"serial": serial}

        for src_key, dst_key in FIELD_MAP.items():
            raw = message.get(src_key)
            if raw not in INVALID_VALUES:
                if isinstance(raw, (int, float)):
                    state[dst_key] = round(float(raw), 6)
                elif isinstance(raw, str):
                    try:
                        state[dst_key] = round(float(raw), 6)
                    except ValueError:
                        pass

        state["last_seen"] = message.get("datetime", "")
        state["type"] = message.get("subtype", message.get("type", ""))
        state["uploader"] = message.get("uploader_callsign", "")

        now = time.time()
        last = self.last_published.get(serial, 0.0)
        if now - last < self.min_publish_interval:
            return
        self.last_published[serial] = now

        # Publish state for this radiosonde
        self._publish(f"sondehub/{safe}/state", state)
        self._publish("sondehub/latest/state", state)

        if self.area_alert_enabled:
            lat = state.get("latitude")
            lon = state.get("longitude")
            if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
                in_area = self._is_in_alert_area(float(lat), float(lon))
                if in_area:
                    self.sondes_in_area.add(serial)
                    area_payload = {
                        "serial": serial,
                        "latitude": lat,
                        "longitude": lon,
                        "altitude": state.get("altitude"),
                        "last_seen": state.get("last_seen", ""),
                        "count_in_area": len(self.sondes_in_area),
                    }
                    self._publish("sondehub/alerts/last_in_area", area_payload)
                else:
                    self.sondes_in_area.discard(serial)

                self._publish(
                    "sondehub/alerts/in_area",
                    "ON" if self.sondes_in_area else "OFF",
                    retain=True,
                )
        
        log.debug(
            "%s: alt=%sm lat=%s lon=%s",
            serial,
            state.get("altitude"),
            state.get("latitude"),
            state.get("longitude"),
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def _shutdown(self, signum, frame) -> None:
        log.info("Shutting down SondeHub add-on...")
        self._publish("sondehub/global/availability", "offline", retain=True)
        for serial in self.announced:
            safe = serial.replace("-", "_").replace(" ", "_").lower()
            self._publish(f"sondehub/{safe}/availability", "offline", retain=True)
        if self.stream is not None:
            try:
                self.stream.disconnect()
            except Exception:
                pass
        if self.mqtt_client is not None:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
        sys.exit(0)

    def run(self) -> None:
        self._connect_mqtt()
        # Give the MQTT connection a moment to establish before publishing discovery
        time.sleep(2)

        self._announce_global_entities()
        self._publish("sondehub/global/availability", "online", retain=True)
        self._publish("sondehub/alerts/in_area", "OFF", retain=True)

        log.info("Starting SondeHub stream...")

        kwargs: dict = {"on_message": self._on_sonde_message}
        if self.filter_serials:
            kwargs["sondes"] = self.filter_serials
            log.info("Filtering to serials: %s", ", ".join(self.filter_serials))
        if self.amateur:
            kwargs["prefix"] = "amateur"
            log.info("Subscribing to amateur high-altitude balloon launches")

        self.stream = sondehub_lib.Stream(**kwargs)  # type: ignore[attr-defined]

        log.info("SondeHub add-on running. Listening for radiosondes...")

        signal.signal(signal.SIGTERM, self._shutdown)
        signal.signal(signal.SIGINT, self._shutdown)

        try:
            while True:
                time.sleep(5)
        except (KeyboardInterrupt, SystemExit):
            self._shutdown(None, None)


def main() -> None:
    opts = load_options()
    addon = SondeHubAddon(opts)
    addon.run()


if __name__ == "__main__":
    main()
