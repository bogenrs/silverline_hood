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

from .const import DOMAIN, STATUS_QUERY, CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL, DEVICE_IDENTIFIER

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

    async def _connect_and_read_initial(self):
        """Connect and read the initial 'okidargb' response."""
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(self.host, self.port), timeout=10
        )
        
        # Read initial response (should be "okidargb")
        try:
            initial_response = await asyncio.wait_for(reader.read(100), timeout=3)
            initial_str = initial_response.decode().strip()
            _LOGGER.debug("Initial response: %s", initial_str)
        except asyncio.TimeoutError:
            _LOGGER.debug("No initial response received")
        
        return reader, writer

    async def _query_status(self) -> Dict[str, Any]:
        """Query the current status from the hood."""
        try:
            # Connect and handle initial response
            reader, writer = await self._connect_and_read_initial()
            
            # Send status query
            query_command = json.dumps(STATUS_QUERY) + '\n'
            writer.write(query_command.encode())
            await writer.drain()
            
            # Read response
            try:
                response = await asyncio.wait_for(reader.read(1024), timeout=5)
                
                if response:
                    response_str = response.decode().strip()
                    _LOGGER.debug("Status response: %s", response_str)
                    
                    # Try to parse as JSON
                    try:
                        status_data = json.loads(response_str)
                        writer.close()
                        await writer.wait_closed()
                        return status_data
                    except json.JSONDecodeError:
                        _LOGGER.debug("Status response is not JSON: %s", response_str)
                
            except asyncio.TimeoutError:
                _LOGGER.debug("No status response received")
            
            writer.close()
            await writer.wait_closed()
            
            # Return last known state if no valid response
            return self._last_sent_state
                
        except asyncio.TimeoutError:
            _LOGGER.error("Timeout querying Silverline Hood at %s:%s", self.host, self.port)
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
            json_command = json.dumps(self._last_sent_state) + '\n'
            
            # Connect and handle initial response
            reader, writer = await self._connect_and_read_initial()
            
            # Send command
            writer.write(json_command.encode())
            await writer.drain()
            
            writer.close()
            await writer.wait_closed()
            
            _LOGGER.debug("Sent command to %s:%s: %s", self.host, self.port, json_command.strip())
            
            #