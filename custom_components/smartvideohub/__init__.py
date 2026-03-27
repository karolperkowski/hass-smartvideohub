import asyncio

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

import logging

from .pyvideohub import SmartVideoHub
from .const import DOMAIN, CONF_HOST, CONF_PORT, CONF_LOG_LEVEL, LOG_LEVELS, DEFAULT_LOG_LEVEL

PLATFORMS = [
    Platform.MEDIA_PLAYER,
    Platform.SELECT,
    Platform.TEXT,
    Platform.BUTTON,
    Platform.SWITCH,
]


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up Smart Video Hub from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Apply saved log level from options
    log_level_name = config_entry.options.get(CONF_LOG_LEVEL, DEFAULT_LOG_LEVEL)
    log_level = LOG_LEVELS.get(log_level_name, logging.WARNING)
    logging.getLogger("custom_components.smartvideohub").setLevel(log_level)

    smartvideohub = SmartVideoHub(
        config_entry.data[CONF_HOST],
        config_entry.data[CONF_PORT],
    )
    smartvideohub.start()
    await smartvideohub.initialised.wait()

    hass.data[DOMAIN][config_entry.entry_id] = {
        "client": smartvideohub,
    }

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN][entry.entry_id]["client"].stop()
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
