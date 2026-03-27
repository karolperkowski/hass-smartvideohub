import logging

from homeassistant.components.select import ENTITY_ID_FORMAT, SelectEntity
from homeassistant.helpers.entity import async_generate_entity_id, DeviceInfo
from .const import DOMAIN, CONF_HOST, MODEL_VIDEOHUB, MODEL_STREAMING, MODEL_TERANEX

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up SmartVideoHub Device"""
    dev = hass.data[DOMAIN][config_entry.entry_id]['client']

    device_info = DeviceInfo(
        identifiers={(DOMAIN, config_entry.entry_id)},
        name=dev.name,
        manufacturer="Blackmagic Design",
        model=dev.model,
        configuration_url=f"http://{config_entry.data[CONF_HOST]}",
    )
    if dev.model == MODEL_STREAMING:
        async_add_entities(
            [
                StreamingSelectDevice(
                    hass,
                    dev,
                    "platform",
                    device_info
                ),
                StreamingSelectDevice(
                    hass,
                    dev,
                    "quality_level",
                    device_info
                ),
                StreamingSelectDevice(
                    hass,
                    dev,
                    "video_mode",
                    device_info
                )
            ],
            True,
        )
    elif dev.model == MODEL_TERANEX:
        async_add_entities(
            [
                StreamingSelectDevice(
                    hass,
                    dev,
                    "lut",
                    device_info
                )
            ],
            True,
        )

class StreamingSelectDevice(SelectEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        hass,
        dev,
        translation_key,
        device_info
    ):
        """Initialize new zone."""
        self._dev = dev
        self._attr_translation_key = translation_key
        self._attr_unique_id = async_generate_entity_id(
            ENTITY_ID_FORMAT,
            dev.attrs.get("Unique ID", "")+"/"+translation_key,
            hass=hass,
        )
        self._attr_device_info = device_info
        dev.add_update_callback(self.update_callback)

    def _split_option(self, key: str, store: dict) -> list[str]:
        """Safely split a comma-separated option string, returning [] if not yet available."""
        value = store.get(key)
        if not value:
            return []
        return [v.strip() for v in value.split(",") if v.strip()]

    def update(self):
        """Retrieve latest state."""
        is_idle = self._dev.stream_state.get("Status") == "Idle" and self._dev.connected
        if self._attr_translation_key == "platform":
            self._attr_current_option = self._dev.stream_set.get("Current Platform")
            self._attr_options = (
                self._split_option("Available Default Platforms", self._dev.stream_set) +
                self._split_option("Available Custom Platforms", self._dev.stream_set)
            )
            self._attr_available = is_idle
        elif self._attr_translation_key == "video_mode":
            self._attr_current_option = self._dev.stream_set.get("Video Mode")
            self._attr_options = self._split_option("Available Video Modes", self._dev.stream_set)
            self._attr_available = is_idle
        elif self._attr_translation_key == "quality_level":
            self._attr_current_option = self._dev.stream_set.get("Current Quality Level")
            self._attr_options = self._split_option("Available Quality Levels", self._dev.stream_set)
            self._attr_available = is_idle
        elif self._attr_translation_key == "lut":
            num_luts = int(self._dev.teranex_set.get("Number of LUTs", 0))
            self._attr_options = ["none"] + ["Lut %d" % x for x in range(num_luts)]
            self._attr_current_option = self._dev.teranex_set.get("Lut selection", "none")
            self._attr_available = self._dev.connected

    async def async_select_option(self, option: str) -> None:
        """Update the current selected option."""
        self._attr_current_option = option
        if self._attr_translation_key == "platform":
            self._dev.set_stream_platform(option)
        elif self._attr_translation_key == "video_mode":
            self._dev.set_video_mode(option)
        elif self._attr_translation_key == "quality_level":
            self._dev.set_quality_level(option)
        elif self._attr_translation_key == "lut":
            self._dev.set_lut(option)
        self.async_write_ha_state()

    def update_callback(self, output_id=0):
        """Called when data is received by pySmartVideoHub"""
        self.update()
        self.schedule_update_ha_state(False)
