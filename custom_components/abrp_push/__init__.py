"""The ABRP Push integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType
import voluptuous as vol

from .const import DOMAIN
from .pusher import AbrpPusher

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SWITCH]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type AbrpConfigEntry = ConfigEntry[AbrpPusher]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the ABRP Push integration (registers domain services)."""

    async def async_handle_push_now(call: ServiceCall) -> None:
        entry_id = call.data.get("entry_id")
        vehicle = call.data.get("vehicle")

        for entry in hass.config_entries.async_entries(DOMAIN):
            pusher: AbrpPusher = entry.runtime_data
            if entry_id and entry.entry_id != entry_id:
                continue
            if vehicle and pusher.vehicle_name.lower() != str(vehicle).lower():
                continue
            await pusher.async_push_now(reason="service")

    hass.services.async_register(
        DOMAIN,
        "push_now",
        async_handle_push_now,
        schema=vol.Schema(
            {
                vol.Optional("entry_id"): cv.string,
                vol.Optional("vehicle"): cv.string,
            }
        ),
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: AbrpConfigEntry) -> bool:
    """Set up ABRP Push from a config entry (one entry per vehicle)."""
    pusher = AbrpPusher(hass, dict(entry.data), dict(entry.options))
    entry.runtime_data = pusher

    async def _async_update_listener(
        hass: HomeAssistant, updated: ConfigEntry
    ) -> None:
        pusher.update_config(dict(updated.data), dict(updated.options))

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await pusher.async_start()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: AbrpConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.async_stop()
    return unload_ok
