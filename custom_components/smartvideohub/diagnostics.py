"""Diagnostics support for Smart Video Hub."""
from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.redact import async_redact_data

from .const import DOMAIN, CONF_HOST

TO_REDACT = {CONF_HOST}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    client = config_entry.runtime_data.client

    return {
        "config_entry": async_redact_data(config_entry.data, TO_REDACT),
        "options": config_entry.options,
        "device": {
            "name": client.name,
            "model": client.model,
            "attrs": client.attrs,
            "connected": client.connected,
            "initialised": client.is_initialised,
        },
        "inputs": {
            "total": len(client.inputs),
            "filtered": len(client.filtered_inputs),
            "labels": client.inputs,
        },
        "outputs": {
            "total": len(client.outputs),
            "routing": {
                output_id: {
                    "name": output.get("name"),
                    "input_id": output.get("input"),
                    "input_name": output.get("input_name"),
                }
                for output_id, output in client.outputs.items()
            },
        },
    }
