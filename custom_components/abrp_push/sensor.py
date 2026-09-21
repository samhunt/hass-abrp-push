"""Sensor platform for ABRP Push status."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import ATTR_LAST_ERROR, ATTR_LAST_SENT, DOMAIN
from .pusher import AbrpPusher


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    pusher: AbrpPusher = entry.runtime_data
    async_add_entities([AbrpPushStatusSensor(entry, pusher)])


class AbrpPushStatusSensor(SensorEntity):
    """Expose last push status and payload attributes."""

    _attr_has_entity_name = True
    _attr_name = "Status"
    _attr_icon = "mdi:map-marker-path"

    def __init__(self, entry: ConfigEntry, pusher: AbrpPusher) -> None:
        self._entry = entry
        self._pusher = pusher
        self._attr_unique_id = f"{entry.entry_id}_status"
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
    def native_value(self) -> str:
        if self._pusher.status_attrs.get(ATTR_LAST_ERROR):
            return "error"
        if self._pusher.status_attrs.get(ATTR_LAST_SENT):
            return "ok"
        return "idle"

    @property
    def extra_state_attributes(self) -> dict:
        return self._pusher.status_attrs
