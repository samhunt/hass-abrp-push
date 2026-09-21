"""Config flow for ABRP Push."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    CONF_API_KEY,
    CONF_BATT_TEMP_ENTITY,
    CONF_CAPACITY_FIXED,
    CONF_CAR_MODEL,
    CONF_CHARGING_ENTITY,
    CONF_CURRENT_ENTITY,
    CONF_DCFC_ENTITY,
    CONF_ELEVATION_ENTITY,
    CONF_EXT_TEMP_ENTITY,
    CONF_HEADING_ENTITY,
    CONF_LATITUDE_ENTITY,
    CONF_LONGITUDE_ENTITY,
    CONF_MAX_STALE_SECONDS,
    CONF_MIN_UPDATE_SECONDS,
    CONF_ODOMETER_ENTITY,
    CONF_PARKED_ENTITY,
    CONF_POSITION_ENTITY,
    CONF_POWER_ENTITY,
    CONF_RANGE_ENTITY,
    CONF_SOC_ENTITY,
    CONF_SOH_ENTITY,
    CONF_SOH_FIXED,
    CONF_SPEED_ENTITY,
    CONF_USER_TOKEN,
    CONF_VEHICLE_NAME,
    CONF_VOLTAGE_ENTITY,
    DEFAULT_CAR_MODEL,
    DEFAULT_MAX_STALE_SECONDS,
    DEFAULT_MIN_UPDATE_SECONDS,
    DOMAIN,
)


def _credentials_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_VEHICLE_NAME,
                default=defaults.get(CONF_VEHICLE_NAME, "My EV"),
            ): selector.TextSelector(),
            vol.Required(
                CONF_API_KEY,
                default=defaults.get(CONF_API_KEY, ""),
            ): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
            ),
            vol.Required(
                CONF_USER_TOKEN,
                default=defaults.get(CONF_USER_TOKEN, ""),
            ): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
            ),
            vol.Optional(
                CONF_CAR_MODEL,
                default=defaults.get(CONF_CAR_MODEL, DEFAULT_CAR_MODEL),
            ): selector.TextSelector(),
            vol.Required(
                CONF_MIN_UPDATE_SECONDS,
                default=defaults.get(
                    CONF_MIN_UPDATE_SECONDS, DEFAULT_MIN_UPDATE_SECONDS
                ),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    max=120,
                    step=1,
                    mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement="s",
                )
            ),
            vol.Required(
                CONF_MAX_STALE_SECONDS,
                default=defaults.get(
                    CONF_MAX_STALE_SECONDS, DEFAULT_MAX_STALE_SECONDS
                ),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    max=600,
                    step=1,
                    mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement="s",
                )
            ),
        }
    )


def _optional_entity(
    schema: dict[Any, Any],
    key: str,
    defaults: dict[str, Any],
    *,
    domain: list[str],
) -> None:
    default = defaults.get(key)
    selector_cfg = selector.EntitySelector(
        selector.EntitySelectorConfig(domain=domain)
    )
    if default:
        schema[vol.Optional(key, default=default)] = selector_cfg
    else:
        schema[vol.Optional(key)] = selector_cfg


def _sensors_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    defaults = defaults or {}
    schema: dict[Any, Any] = {
        vol.Required(
            CONF_SOC_ENTITY,
            default=defaults.get(CONF_SOC_ENTITY),
        ): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["sensor", "number"])
        ),
    }

    _optional_entity(schema, CONF_SPEED_ENTITY, defaults, domain=["sensor", "number"])
    _optional_entity(schema, CONF_POWER_ENTITY, defaults, domain=["sensor", "number"])
    _optional_entity(
        schema, CONF_POSITION_ENTITY, defaults, domain=["device_tracker", "person"]
    )
    _optional_entity(
        schema, CONF_LATITUDE_ENTITY, defaults, domain=["sensor", "number"]
    )
    _optional_entity(
        schema, CONF_LONGITUDE_ENTITY, defaults, domain=["sensor", "number"]
    )
    _optional_entity(
        schema,
        CONF_CHARGING_ENTITY,
        defaults,
        domain=["binary_sensor", "sensor", "switch"],
    )
    _optional_entity(
        schema,
        CONF_DCFC_ENTITY,
        defaults,
        domain=["binary_sensor", "sensor", "switch"],
    )
    _optional_entity(
        schema, CONF_PARKED_ENTITY, defaults, domain=["binary_sensor", "sensor"]
    )
    _optional_entity(
        schema, CONF_EXT_TEMP_ENTITY, defaults, domain=["sensor", "number"]
    )
    _optional_entity(
        schema, CONF_BATT_TEMP_ENTITY, defaults, domain=["sensor", "number"]
    )
    _optional_entity(
        schema, CONF_ODOMETER_ENTITY, defaults, domain=["sensor", "number"]
    )
    _optional_entity(schema, CONF_RANGE_ENTITY, defaults, domain=["sensor", "number"])
    _optional_entity(schema, CONF_SOH_ENTITY, defaults, domain=["sensor", "number"])
    _optional_entity(
        schema, CONF_VOLTAGE_ENTITY, defaults, domain=["sensor", "number"]
    )
    _optional_entity(
        schema, CONF_CURRENT_ENTITY, defaults, domain=["sensor", "number"]
    )
    _optional_entity(
        schema, CONF_HEADING_ENTITY, defaults, domain=["sensor", "number"]
    )
    _optional_entity(
        schema, CONF_ELEVATION_ENTITY, defaults, domain=["sensor", "number"]
    )

    soh_sel = selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=0,
            max=100,
            step=0.1,
            mode=selector.NumberSelectorMode.BOX,
            unit_of_measurement="%",
        )
    )
    capacity_sel = selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=0,
            max=300,
            step=0.1,
            mode=selector.NumberSelectorMode.BOX,
            unit_of_measurement="kWh",
        )
    )
    soh_default = defaults.get(CONF_SOH_FIXED)
    capacity_default = defaults.get(CONF_CAPACITY_FIXED)
    if soh_default is not None:
        schema[vol.Optional(CONF_SOH_FIXED, default=soh_default)] = soh_sel
    else:
        schema[vol.Optional(CONF_SOH_FIXED)] = soh_sel
    if capacity_default is not None:
        schema[vol.Optional(CONF_CAPACITY_FIXED, default=capacity_default)] = (
            capacity_sel
        )
    else:
        schema[vol.Optional(CONF_CAPACITY_FIXED)] = capacity_sel

    return vol.Schema(schema)


class AbrpPushConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ABRP Push (one entry per vehicle)."""

    VERSION = 1

    def __init__(self) -> None:
        self._credentials: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Collect API credentials and vehicle identity."""
        errors: dict[str, str] = {}

        if user_input is not None:
            api_key = str(user_input[CONF_API_KEY]).strip()
            token = str(user_input[CONF_USER_TOKEN]).strip()
            name = str(user_input[CONF_VEHICLE_NAME]).strip()

            if not api_key or not token or not name:
                errors["base"] = "invalid_credentials"
            else:
                await self.async_set_unique_id(token)
                self._abort_if_unique_id_configured()
                self._credentials = {
                    CONF_VEHICLE_NAME: name,
                    CONF_API_KEY: api_key,
                    CONF_USER_TOKEN: token,
                    CONF_CAR_MODEL: str(user_input.get(CONF_CAR_MODEL, "")).strip(),
                    CONF_MIN_UPDATE_SECONDS: int(user_input[CONF_MIN_UPDATE_SECONDS]),
                    CONF_MAX_STALE_SECONDS: int(user_input[CONF_MAX_STALE_SECONDS]),
                }
                return await self.async_step_sensors()

        return self.async_show_form(
            step_id="user",
            data_schema=_credentials_schema(),
            errors=errors,
        )

    async def async_step_sensors(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Map Home Assistant entities to ABRP telemetry fields."""
        errors: dict[str, str] = {}

        if user_input is not None:
            if not user_input.get(CONF_SOC_ENTITY):
                errors["base"] = "soc_required"
            else:
                cleaned = {k: v for k, v in user_input.items() if v not in (None, "")}
                return self.async_create_entry(
                    title=self._credentials[CONF_VEHICLE_NAME],
                    data={**self._credentials, **cleaned},
                )

        return self.async_show_form(
            step_id="sensors",
            data_schema=_sensors_schema(),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> AbrpPushOptionsFlow:
        return AbrpPushOptionsFlow()


class AbrpPushOptionsFlow(config_entries.OptionsFlow):
    """Reconfigure credentials, intervals, and sensor mappings."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            if not user_input.get(CONF_SOC_ENTITY):
                errors["base"] = "soc_required"
            else:
                cleaned = {k: v for k, v in user_input.items() if v not in (None, "")}
                cleaned[CONF_MIN_UPDATE_SECONDS] = int(
                    cleaned[CONF_MIN_UPDATE_SECONDS]
                )
                cleaned[CONF_MAX_STALE_SECONDS] = int(cleaned[CONF_MAX_STALE_SECONDS])
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    title=cleaned[CONF_VEHICLE_NAME],
                    data=cleaned,
                    options={},
                )
                return self.async_create_entry(title="", data={})

        defaults = {**self.config_entry.data, **self.config_entry.options}
        schema = vol.Schema(
            {
                **_credentials_schema(defaults).schema,
                **_sensors_schema(defaults).schema,
            }
        )
        return self.async_show_form(
            step_id="init", data_schema=schema, errors=errors
        )
