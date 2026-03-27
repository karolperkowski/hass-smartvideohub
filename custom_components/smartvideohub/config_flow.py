from __future__ import annotations

import asyncio
import logging

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN, CONF_HOST, CONF_PORT, DEFAULT_PORT
from .pyvideohub import SmartVideoHub

STEP_USER_DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_HOST): str,
    vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
})

_LOGGER = logging.getLogger(__name__)


async def validate_input(hass: HomeAssistant, data: dict) -> dict[str, str]:
    """Validate the user input allows us to connect."""
    client = SmartVideoHub(data[CONF_HOST], data[CONF_PORT])
    client.start()
    try:
        await asyncio.wait_for(client.initialised.wait(), timeout=10)
        return {"title": client.name or data[CONF_HOST]}
    except asyncio.TimeoutError:
        raise ValueError("cannot_connect")
    except Exception as e:
        _LOGGER.error("Communication error: %s: %s", e.__class__.__name__, str(e))
        raise ValueError("communication_error") from e
    finally:
        client.stop()


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Smart Video Hub."""

    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
                return self.async_create_entry(title=info["title"], data=user_input)
            except (ConnectionError, ConnectionRefusedError):
                errors["base"] = "cannot_connect"
            except ValueError as e:
                errors["base"] = str(e) if str(e) in ("cannot_connect", "communication_error") else "unknown"
                if errors["base"] == "unknown":
                    _LOGGER.error("Unexpected error: %s", e)
            except Exception as e:
                _LOGGER.error("Unexpected error: %s: %s", e.__class__.__name__, e)
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
