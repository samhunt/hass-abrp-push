"""Switch platform for ABRP Push."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .pusher import AbrpPusher


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    pusher: AbrpPusher = entry.runtime_data
    async_add_entities([AbrpPushSwitch(entry, pusher)])


class AbrpPushSwitch(SwitchEntity):
    """Enable or disable telemetry upload for one vehicle."""

    _attr_has_entity_name = True
    _attr_name = "Upload"
    _attr_icon = "mdi:cloud-upload"

    def __init__(self, entry: ConfigEntry, pusher: AbrpPusher) -> None:
        self._entry = entry
        self._pusher = pusher
        self._attr_unique_id = f"{entry.entry_id}_upload"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=pusher.vehicle_name,
            manufacturer="Iternio",
            model="ABRP Telemetry",
        )

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self._pusher.async_add_listener(self._handle_update))

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()

    @property
    def is_on(self) -> bool:
        return self._pusher.enabled

    async def async_turn_on(self, **kwargs) -> None:
        self._pusher.set_enabled(True)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        self._pusher.set_enabled(False)
        self.async_write_ha_state()
