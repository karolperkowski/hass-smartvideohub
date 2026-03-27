import asyncio
import logging
from dataclasses import dataclass

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


@dataclass
class SmartVideoHubData:
    """Runtime data stored on the config entry."""
    client: SmartVideoHub


type SmartVideoHubConfigEntry = ConfigEntry[SmartVideoHubData]


async def _async_remove_orphaned_entities(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Remove entity registry entries left behind by the temporary MAC-prefixed unique_id."""
    registry = er.async_get(hass)
    unique_id = None

    for entity in er.async_entries_for_config_entry(registry, config_entry.entry_id):
        if entity.unique_id and entity.unique_id.startswith("smartvideohub_output_"):
            parts = entity.entity_id.split(".")
            if len(parts) == 2:
                object_id = parts[1]
                candidate = object_id[:12]
                if len(candidate) == 12 and all(c in "0123456789abcdef" for c in candidate):
                    unique_id = candidate
                    break

    if not unique_id:
        for entity in er.async_entries_for_config_entry(registry, config_entry.entry_id):
            if entity.unique_id and "_output_" in entity.unique_id and entity.unique_id.count("_") > 2:
                unique_id = entity.unique_id.split("_")[1]
                break

    if not unique_id:
        return

    orphan_prefix = f"smartvideohub_{unique_id}_output_"
    removed = 0
    for entity in er.async_entries_for_config_entry(registry, config_entry.entry_id):
        if entity.unique_id and entity.unique_id.startswith(orphan_prefix):
            _LOGGER.info("Removing orphaned entity: %s (%s)", entity.entity_id, entity.unique_id)
            registry.async_remove(entity.entity_id)
            removed += 1

    if removed:
        _LOGGER.info("Removed %i orphaned entity registry entries", removed)


async def async_setup_entry(hass: HomeAssistant, config_entry: SmartVideoHubConfigEntry) -> bool:
    """Set up Smart Video Hub from a config entry."""
    log_level_name = config_entry.options.get(CONF_LOG_LEVEL, DEFAULT_LOG_LEVEL)
    log_level = LOG_LEVELS.get(log_level_name, logging.WARNING)
    logging.getLogger("custom_components.smartvideohub").setLevel(log_level)

    await _async_remove_orphaned_entities(hass, config_entry)

    client = SmartVideoHub(
        config_entry.data[CONF_HOST],
        config_entry.data[CONF_PORT],
    )
    client.start()
    await client.initialised.wait()

    config_entry.runtime_data = SmartVideoHubData(client=client)

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: SmartVideoHubConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        entry.runtime_data.client.stop()
    return unload_ok
