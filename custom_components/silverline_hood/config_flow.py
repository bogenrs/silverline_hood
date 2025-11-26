"""Config flow for Silverline Hood integration."""
import asyncio
import json
import logging
from typing import Any, Dict, Optional

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    DEFAULT_PORT,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    CONF_UPDATE_INTERVAL,
    MIN_UPDATE_INTERVAL,
    MAX_UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
    }
)


async def validate_input(hass: HomeAssistant, data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate the user input allows us to connect."""
    host = data[CONF_HOST]
    port = data[CONF_PORT]

    try:
        # Test connection with status query
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=5
        )
        
        # Send status query
        test_command = json.dumps({"A": 4})
        writer.write(test_command.encode() + b'\n')
        await writer.drain()
        
        # Try to read response
        response = await asyncio.wait_for(reader.readline(), timeout=5)
        
        writer.close()
        await writer.wait_closed()
        
        # Validate response format
        if response:
            json.loads(response.decode().strip())
        
    except asyncio.TimeoutError:
        raise CannotConnect
    except json.JSONDecodeError:
        _LOGGER.warning("Device responded but with invalid JSON")
        # Still allow connection as device might work for commands
    except Exception:
        raise CannotConnect

    return {"title": f"Silverline Hood ({host})"}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Silverline Hood."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", 
                data_schema=STEP_USER_DATA_SCHEMA,
                description_placeholders={
                    "name": "Silverline Hood"
                }
            )

        errors = {}

        try:
            info = await validate_input(self.hass, user_input)
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            await self.async_set_unique_id(user_input[CONF_HOST])
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", 
            data_schema=STEP_USER_DATA_SCHEMA, 
            errors=errors,
            description_placeholders={
                "name": "Silverline Hood"
            }
        )


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Silverline Hood."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Get current coordinator to show current interval
        coordinator = None
        if DOMAIN in self.hass.data and self.config_entry.entry_id in self.hass.data[DOMAIN]:
            coordinator = self.hass.data[DOMAIN][self.config_entry.entry_id]

        current_interval = DEFAULT_UPDATE_INTERVAL
        if coordinator:
            current_interval = coordinator.update_interval_seconds()
        else:
            current_interval = self.config_entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)

        options_schema = vol.Schema(
            {
                vol.Required(
                    CONF_HOST,
                    default=self.config_entry.options.get(
                        CONF_HOST, self.config_entry.data.get(CONF_HOST)
                    ),
                ): str,
                vol.Required(
                    CONF_PORT,
                    default=self.config_entry.options.get(
                        CONF_PORT, self.config_entry.data.get(CONF_PORT)
                    ),
                ): int,
                vol.Required(
                    CONF_UPDATE_INTERVAL,
                    default=current_interval,
                ): vol.All(vol.Coerce(int), vol.Range(min=MIN_UPDATE_INTERVAL, max=MAX_UPDATE_INTERVAL)),
            }
        )

        return self.async_show_form(
            step_id="init", 
            data_schema=options_schema,
            description_placeholders={
                "min_interval": str(MIN_UPDATE_INTERVAL),
                "max_interval": str(MAX_UPDATE_INTERVAL),
                "current_interval": str(current_interval),
            }
        )


class CannotConnect(Exception):
    """Error to indicate we cannot connect."""