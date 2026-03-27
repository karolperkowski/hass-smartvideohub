"""Support for interfacing with Blackmagic Smart Video Hub."""
from __future__ import annotations

import logging

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerState,
    MediaPlayerEntityFeature,
    MediaPlayerDeviceClass,
    ENTITY_ID_FORMAT,
)
from homeassistant.helpers.entity import async_generate_entity_id, DeviceInfo

from .const import DOMAIN, MODEL_VIDEOHUB, CONF_HIDE_DEFAULT_INPUTS

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Smart Video Hub media player entities."""
    dev = hass.data[DOMAIN][config_entry.entry_id]["client"]

    device_info = DeviceInfo(
        identifiers={(DOMAIN, config_entry.entry_id)},
        name=dev.name,
        manufacturer="Blackmagic Design",
        model=dev.model,
    )

    if dev.model == MODEL_VIDEOHUB:
        _LOGGER.info("Adding %i outputs", len(dev.get_outputs()))
        async_add_entities(
            [
                SmartVideoHubOutput(
                    hass,
                    dev,
                    dev.attrs.get("Unique ID"),
                    output_number,
                    output,
                    device_info,
                    hide_default_inputs=config_entry.data.get(CONF_HIDE_DEFAULT_INPUTS, False),
                )
                for output_number, output in dev.get_outputs().items()
            ],
            True,
        )


class SmartVideoHubOutput(MediaPlayerEntity):
    """Representation of a Blackmagic Smart Video Hub output."""

    _attr_supported_features = MediaPlayerEntityFeature.SELECT_SOURCE
    _attr_device_class = MediaPlayerDeviceClass.RECEIVER
    _attr_should_poll = False

    def __init__(
        self,
        hass,
        smartvideohub,
        entity_prefix,
        output_number,
        output,
        device_info,
        hide_default_inputs=False,
    ):
        """Initialise the output entity."""
        _LOGGER.info("Adding SmartVideoHub output %i", output_number)
        self._smartvideohub = smartvideohub
        self._output_id = output_number
        self._output_name = output.get("name", "Output %d" % output_number)
        self._source_id = output["input"]
        self._attr_source = smartvideohub.get_input_name(self._source_id)
        self._connected = smartvideohub.connected
        self._hide_default_inputs = hide_default_inputs
        self._attr_source_list = smartvideohub.get_input_list(hide_default_inputs)
        self._attr_unique_id = f"smartvideohub_{entity_prefix}_output_{output_number}"
        self.entity_id = async_generate_entity_id(
            ENTITY_ID_FORMAT,
            (entity_prefix + " " if entity_prefix else "") + output.get("name", "output_" + str(output_number)),
            hass=hass,
        )
        self._attr_device_info = device_info
        smartvideohub.add_update_callback(self.update_callback)

    def update(self):
        """Retrieve latest state."""
        self._output_name = self._smartvideohub.get_outputs()[self._output_id].get("name")
        self._source_id = self._smartvideohub.get_selected_input(self._output_id)
        self._attr_source = self._smartvideohub.get_input_name(self._source_id)
        self._connected = self._smartvideohub.connected
        self._attr_source_list = self._smartvideohub.get_input_list(self._hide_default_inputs)

    @property
    def name(self) -> str:
        """Return the name of the output."""
        return self._output_name

    @property
    def state(self):
        """Return the current source as the state."""
        if not self._connected:
            return MediaPlayerState.OFF
        if self._attr_source:
            return self._attr_source
        return MediaPlayerState.ON

    @property
    def media_title(self) -> str | None:
        """Return the current source as the media title."""
        return self._attr_source

    def select_source(self, source: str) -> None:
        """Set the input source."""
        self._smartvideohub.set_input_by_name(self._output_id, source)

    def update_callback(self, output_id=0) -> None:
        """Called when data is received from the device."""
        if output_id == 0 or output_id == self._output_id:
            _LOGGER.debug("Status update for output %i", output_id)
            self.update()
            self.schedule_update_ha_state(False)
