"""Support for Silverline Hood Sensors."""
import logging
from typing import Any, Optional

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.const import PERCENTAGE, SIGNAL_STRENGTH_DECIBELS

from .const import (
    DOMAIN,
    CMD_WIFI_AP_SSID,
    CMD_WIFI_AP_PASS,
    CMD_WIFI_SSID,
    CMD_WIFI_MODE,
    CMD_T,
    CMD_TM,
    CMD_TS,
    CMD_UNKNOWN_U,
    CMD_LIGHT_MODE,
    CMD_CW_DIRECTION,
    CMD_RGB_DIRECTION,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Silverline Hood sensors."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    sensors = [
        SilverlineHoodWifiSSIDSensor(coordinator),
        SilverlineHoodWifiModeSensor(coordinator),
        SilverlineHoodWifiAPSSIDSensor(coordinator),
        SilverlineHoodTemperatureSensor(coordinator),
        SilverlineHoodTimerSensor(coordinator, "TM", "Timer TM"),
        SilverlineHoodTimerSensor(coordinator, "TS", "Timer TS"),
        SilverlineHoodStatusSensor(coordinator, "U", "Status U"),
        SilverlineHoodLightModeSensor(coordinator),
        SilverlineHoodDirectionSensor(coordinator, "CWD", "Cold White Direction"),
        SilverlineHoodDirectionSensor(coordinator, "RGBD", "RGB Direction"),
    ]
    
    async_add_entities(sensors, True)
    _LOGGER.info("Added %d Silverline Hood sensors", len(sensors))


class SilverlineHoodBaseSensor(SensorEntity):
    """Base sensor for Silverline Hood."""

    def __init__(self, coordinator, sensor_type: str, name: str):
        """Initialize the sensor."""
        self._coordinator = coordinator
        self._sensor_type = sensor_type
        self._attr_name = f"Silverline Hood {name}"
        self._attr_unique_id = f"{coordinator.host}_{coordinator.port}_{sensor_type.lower()}"
        self._attr_should_poll = False

    @property
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, f"{self._coordinator.host}_{self._coordinator.port}")},
            "name": "Silverline Hood",
            "manufacturer": "Silverline",
            "model": "Smart Hood",
        }

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return True


class SilverlineHoodWifiSSIDSensor(SilverlineHoodBaseSensor):
    """WiFi SSID sensor."""

    def __init__(self, coordinator):
        """Initialize the sensor."""
        super().__init__(coordinator, "wifi_ssid", "WiFi SSID")
        self._attr_icon = "mdi:wifi"

    @property
    def native_value(self) -> Optional[str]:
        """Return the WiFi SSID."""
        return self._coordinator.current_state.get(CMD_WIFI_SSID, "Unknown")


class SilverlineHoodWifiModeSensor(SilverlineHoodBaseSensor):
    """WiFi Mode sensor."""

    def __init__(self, coordinator):
        """Initialize the sensor."""
        super().__init__(coordinator, "wifi_mode", "WiFi Mode")
        self._attr_icon = "mdi:wifi-settings"

    @property
    def native_value(self) -> Optional[str]:
        """Return the WiFi mode."""
        mode = self._coordinator.current_state.get(CMD_WIFI_MODE, "Unknown")
        # Translate common modes
        mode_map = {
            "STA": "Station",
            "AP": "Access Point", 
            "AP_STA": "Mixed Mode"
        }
        return mode_map.get(mode, mode)


class SilverlineHoodWifiAPSSIDSensor(SilverlineHoodBaseSensor):
    """WiFi Access Point SSID sensor."""

    def __init__(self, coordinator):
        """Initialize the sensor."""
        super().__init__(coordinator, "wifi_ap_ssid", "WiFi Hotspot Name")
        self._attr_icon = "mdi:wifi-strength-4"

    @property
    def native_value(self) -> Optional[str]:
        """Return the WiFi AP SSID."""
        return self._coordinator.current_state.get(CMD_WIFI_AP_SSID, "Unknown")


class SilverlineHoodTemperatureSensor(SilverlineHoodBaseSensor):
    """Temperature sensor."""

    def __init__(self, coordinator):
        """Initialize the sensor."""
        super().__init__(coordinator, "temperature", "Temperature")
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = "°C"
        self._attr_icon = "mdi:thermometer"

    @property
    def native_value(self) -> Optional[int]:
        """Return the temperature."""
        temp = self._coordinator.current_state.get(CMD_T, 0)
        # Falls T wirklich Temperatur ist, sonst None wenn immer 0
        return temp if temp > 0 else None


class SilverlineHoodTimerSensor(SilverlineHoodBaseSensor):
    """Timer sensor."""

    def __init__(self, coordinator, timer_key: str, name: str):
        """Initialize the sensor."""
        super().__init__(coordinator, timer_key.lower(), name)
        self._timer_key = timer_key
        self._attr_icon = "mdi:timer"
        self._attr_native_unit_of_measurement = "min"

    @property
    def native_value(self) -> Optional[int]:
        """Return the timer value."""
        return self._coordinator.current_state.get(self._timer_key, 0)


class SilverlineHoodStatusSensor(SilverlineHoodBaseSensor):
    """Status sensor."""

    def __init__(self, coordinator, status_key: str, name: str):
        """Initialize the sensor."""
        super().__init__(coordinator, status_key.lower(), name)
        self._status_key = status_key
        self._attr_icon = "mdi:information"

    @property
    def native_value(self) -> Optional[int]:
        """Return the status value."""
        return self._coordinator.current_state.get(self._status_key, 0)


class SilverlineHoodLightModeSensor(SilverlineHoodBaseSensor):
    """Light mode sensor."""

    def __init__(self, coordinator):
        """Initialize the sensor."""
        super().__init__(coordinator, "light_mode", "Light Mode")
        self._attr_icon = "mdi:lightbulb-on"

    @property
    def native_value(self) -> Optional[str]:
        """Return the light mode."""
        mode = self._coordinator.current_state.get(CMD_LIGHT_MODE, 0)
        mode_map = {
            0: "Normal",
            1: "Breathing", 
            2: "Strobe",
            3: "Fade"
        }
        return mode_map.get(mode, f"Mode {mode}")


class SilverlineHoodDirectionSensor(SilverlineHoodBaseSensor):
    """Direction sensor."""

    def __init__(self, coordinator, direction_key: str, name: str):
        """Initialize the sensor."""
        super().__init__(coordinator, direction_key.lower(), name)
        self._direction_key = direction_key
        self._attr_icon = "mdi:arrow-right"

    @property
    def native_value(self) -> Optional[str]:
        """Return the direction."""
        direction = self._coordinator.current_state.get(self._direction_key, 0)
        direction_map = {
            0: "Off",
            1: "Forward",
            2: "Reverse"
        }
        return direction_map.get(direction, f"Direction {direction}")


# Zusätzlicher WiFi Signal Sensor (falls verfügbar)
class SilverlineHoodSignalStrengthSensor(SilverlineHoodBaseSensor):
    """WiFi signal strength sensor."""

    def __init__(self, coordinator):
        """Initialize the sensor."""
        super().__init__(coordinator, "signal_strength", "WiFi Signal")
        self._attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = SIGNAL_STRENGTH_DECIBELS
        self._attr_icon = "mdi:wifi-strength-3"

    @property
    def native_value(self) -> Optional[int]:
        """Return the signal strength."""
        # Schauen ob es ein RSSI Feld gibt - falls nicht, None zurückgeben
        rssi = self._coordinator.current_state.get("RSSI")
        if rssi is not None:
            return rssi
        
        # Alternative: aus anderen Daten ableiten oder Status-Query erweitern
        return None