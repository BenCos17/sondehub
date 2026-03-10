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

# SondeHub fields -> HA-friendly names (field, friendly_name, unit, device_class, icon)
SENSOR_DEFS = [
    ("altitude",         "Altitude",          "m",    "distance",      None),
    ("temperature",      "Temperature",        "°C",   "temperature",   None),
    ("humidity",         "Humidity",           "%",    "humidity",      None),
    ("latitude",         "Latitude",           "°",    None,            "mdi:latitude"),
    ("longitude",        "Longitude",          "°",    None,            "mdi:longitude"),
    ("speed_horizontal", "Horizontal Speed",   "m/s",  None,            "mdi:speedometer"),
    ("speed_vertical",   "Vertical Speed",     "m/s",  None,            "mdi:arrow-up-down"),
    ("heading",          "Heading",            "°",    None,            "mdi:compass"),
    ("satellites",       "GPS Satellites",     None,   None,            "mdi:satellite-variant"),
    ("battery",          "Battery Voltage",    "V",    "voltage",       None),
    ("frequency",        "Frequency",          "MHz",  "frequency",     None),
    ("frame",            "Frame Number",       None,   None,            "mdi:counter"),
    ("rssi",             "RSSI",               "dBm",  "signal_strength", None),
]

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

        self.announced: set = set()
        self.mqtt_client: mqtt.Client | None = None
        self.stream = None
        
        # Single addon device shared by all sensors
        self.addon_device: dict = {
            "identifiers": ["sondehub_addon"],
            "name": "bencos17_SondeHub",
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

    def _announce_sonde(self, serial: str, payload: dict) -> None:
        """Publish MQTT Discovery configs for a newly seen radiosonde."""
        safe = serial.replace("-", "_").replace(" ", "_").lower()
        state_topic = f"sondehub/{safe}/state"

        # Remove old retained tracker discovery if it exists from previous versions.
        self._publish(f"homeassistant/device_tracker/sondehub/{safe}/config", "", retain=True)

        for field, friendly_name, unit, device_class, icon in SENSOR_DEFS:
            cfg: dict = {
                "name": f"{friendly_name}",
                "unique_id": f"sondehub_{safe}_{field}",
                "state_topic": state_topic,
                "value_template": f"{{{{ value_json.{field} | default(none) }}}}",
                "availability_topic": f"sondehub/{safe}/availability",
                "device": self.addon_device,
            }
            if unit:
                cfg["unit_of_measurement"] = unit
            if device_class:
                cfg["device_class"] = device_class
            if icon:
                cfg["icon"] = icon

            disc_topic = f"homeassistant/sensor/sondehub/{safe}_{field}/config"
            self._publish(disc_topic, cfg, retain=True)

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
                try:
                    state[dst_key] = round(float(raw), 6)
                except (TypeError, ValueError):
                    pass

        state["last_seen"] = message.get("datetime", "")
        state["type"] = message.get("subtype", message.get("type", ""))
        state["uploader"] = message.get("uploader_callsign", "")

        # Publish state for this radiosonde
        self._publish(f"sondehub/{safe}/state", state)
        
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

        log.info("Starting SondeHub stream...")

        kwargs: dict = {"on_message": self._on_sonde_message}
        if self.filter_serials:
            kwargs["sondes"] = self.filter_serials
            log.info("Filtering to serials: %s", ", ".join(self.filter_serials))
        if self.amateur:
            kwargs["prefix"] = "amateur"
            log.info("Subscribing to amateur high-altitude balloon launches")

        self.stream = sondehub_lib.Stream(**kwargs)

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
