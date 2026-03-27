import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .pyvideohub import SmartVideoHub
from .const import DOMAIN, CONF_HOST, CONF_PORT, CONF_LOG_LEVEL, LOG_LEVELS, DEFAULT_LOG_LEVEL

PLATFORMS = [
    Platform.MEDIA_PLAYER,
    Platform.SELECT,
    Platform.TEXT,
    Platform.BUTTON,
    Platform.SWITCH,
]

_LOGGER = logging.getLogger(__name__)


async def _async_remove_orphaned_entities(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Remove entity registry entries left behind by the temporary MAC-prefixed unique_id.

    During development the unique_id was briefly changed from
    'smartvideohub_output_N' to 'smartvideohub_<MAC>_output_N', creating
    duplicate registry entries. This cleans them up on first run after
    reverting so users don't have to delete 40 entities manually.
    """
    registry = er.async_get(hass)
    unique_id = None

    # Find the MAC address from any existing correctly-formed entry
    # so we know what prefix to look for
    for entity in er.async_entries_for_config_entry(registry, config_entry.entry_id):
        if entity.unique_id and entity.unique_id.startswith("smartvideohub_output_"):
            # Extract MAC from entity_id if possible (e.g. media_player.7c2e0d0a2d90_...)
            parts = entity.entity_id.split(".")
            if len(parts) == 2:
                object_id = parts[1]
                # MAC is the first 12 hex chars
                candidate = object_id[:12]
                if len(candidate) == 12 and all(c in "0123456789abcdef" for c in candidate):
                    unique_id = candidate
                    break

    if not unique_id:
        # Try to get it from attrs stored during a previous run
        for entity in er.async_entries_for_config_entry(registry, config_entry.entry_id):
            if entity.unique_id and "_output_" in entity.unique_id and entity.unique_id.count("_") > 2:
                # Looks like 'smartvideohub_7c2e0d0a2d90_output_N'
                unique_id = entity.unique_id.split("_")[1]
                break

    if not unique_id:
        return

    orphan_prefix = f"smartvideohub_{unique_id}_output_"
    removed = 0
    for entity in er.async_entries_for_config_entry(registry, config_entry.entry_id):
        if entity.unique_id and entity.unique_id.startswith(orphan_prefix):
            _LOGGER.info("Removing orphaned entity registry entry: %s (%s)", entity.entity_id, entity.unique_id)
            registry.async_remove(entity.entity_id)
            removed += 1

    if removed:
        _LOGGER.info("Removed %i orphaned entity registry entries", removed)


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up Smart Video Hub from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Apply saved log level from options
    log_level_name = config_entry.options.get(CONF_LOG_LEVEL, DEFAULT_LOG_LEVEL)
    log_level = LOG_LEVELS.get(log_level_name, logging.WARNING)
    logging.getLogger("custom_components.smartvideohub").setLevel(log_level)

    # Clean up any orphaned entities from the temporary MAC-prefixed unique_id
    await _async_remove_orphaned_entities(hass, config_entry)

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
