"""The Silverline Hood integration."""
import asyncio
import json
import logging
from datetime import timedelta
from typing import Any, Dict

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import DOMAIN, STATUS_QUERY, CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["fan", "light"]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Silverline Hood component."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Silverline Hood from a config entry."""
    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]
    update_interval = entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)

    coordinator = SilverlineHoodCoordinator(hass, host, port, update_interval)
    
    # Fetch initial data so we have data when entities are loaded
    await coordinator.async_config_entry_first_refresh()
    
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Set up options update listener
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options are changed."""
    await hass.config_entries.async_reload(entry.entry_id)


class SilverlineHoodCoordinator(DataUpdateCoordinator):
    """Coordinator for Silverline Hood communication."""

    def __init__(self, hass: HomeAssistant, host: str, port: int, update_interval: int):
        """Initialize the coordinator."""
        self.host = host
        self.port = port
        self._last_sent_state = {
            "M": 0,
            "L": 0,
            "R": 255,
            "G": 255,
            "B": 255,
            "CW": 255,
            "BRG": 255,
            "T": 0,
            "TM": 0,
            "TS": 255,
            "A": 1,
        }

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=update_interval),
        )

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from the hood."""
        try:
            return await self._query_status()
        except Exception as ex:
            raise UpdateFailed(f"Error communicating with Silverline Hood: {ex}")

    async def _query_status(self) -> Dict[str, Any]:
        """Query the current status from the hood."""
        try:
            # Open connection
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port), timeout=5
            )
            
            # Send status query
            query_command = json.dumps(STATUS_QUERY)
            writer.write(query_command.encode() + b'\n')
            await writer.drain()
            
            # Read response
            response = await asyncio.wait_for(reader.readline(), timeout=5)
            
            # Close connection
            writer.close()
            await writer.wait_closed()
            
            # Parse response
            if response:
                status_data = json.loads(response.decode().strip())
                _LOGGER.debug("Received status from %s:%s: %s", self.host, self.port, status_data)
                return status_data
            else:
                _LOGGER.warning("No response received from Silverline Hood")
                return self._last_sent_state
                
        except asyncio.TimeoutError:
            _LOGGER.error("Timeout querying Silverline Hood at %s:%s", self.host, self.port)
            raise
        except json.JSONDecodeError as ex:
            _LOGGER.error("Invalid JSON response from Silverline Hood: %s", ex)
            raise
        except Exception as ex:
            _LOGGER.error("Error querying Silverline Hood: %s", ex)
            raise

    async def send_command(self, command: Dict[str, Any]) -> bool:
        """Send command to the Silverline Hood via Telnet."""
        try:
            # Update the last sent state with the command
            self._last_sent_state.update(command)
            
            # Convert to JSON string
            json_command = json.dumps(self._last_sent_state)
            
            # Send via Telnet
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port), timeout=5
            )
            
            writer.write(json_command.encode() + b'\n')
            await writer.drain()
            
            writer.close()
            await writer.wait_closed()
            
            _LOGGER.debug("Sent command to %s:%s: %s", self.host, self.port, json_command)
            
            # Request immediate refresh to get updated status
            await self.async_request_refresh()
            
            return True
            
        except Exception as ex:
            _LOGGER.error("Error sending command to Silverline Hood: %s", ex)
            return False

    @property
    def current_state(self) -> Dict[str, Any]:
        """Return current state from coordinator data."""
        return self.data if self.data else self._last_sent_state

    def update_interval_seconds(self) -> int:
        """Return current update interval in seconds."""
        return int(self.update_interval.total_seconds())