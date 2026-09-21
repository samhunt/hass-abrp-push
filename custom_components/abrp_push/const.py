"""Constants for the ABRP Push integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "abrp_push"

ABRP_API_URL: Final = "https://api.iternio.com/1/tlm/send"

# Config entry data / options
CONF_API_KEY: Final = "api_key"
CONF_USER_TOKEN: Final = "user_token"
CONF_VEHICLE_NAME: Final = "vehicle_name"
CONF_CAR_MODEL: Final = "car_model"
CONF_MIN_UPDATE_SECONDS: Final = "min_update_seconds"
CONF_MAX_STALE_SECONDS: Final = "max_stale_seconds"

# Sensor entity mappings (options)
CONF_SOC_ENTITY: Final = "soc_entity"
CONF_SPEED_ENTITY: Final = "speed_entity"
CONF_POWER_ENTITY: Final = "power_entity"
CONF_POSITION_ENTITY: Final = "position_entity"
CONF_LATITUDE_ENTITY: Final = "latitude_entity"
CONF_LONGITUDE_ENTITY: Final = "longitude_entity"
CONF_CHARGING_ENTITY: Final = "charging_entity"
CONF_DCFC_ENTITY: Final = "dcfc_entity"
CONF_PARKED_ENTITY: Final = "parked_entity"
CONF_EXT_TEMP_ENTITY: Final = "ext_temp_entity"
CONF_BATT_TEMP_ENTITY: Final = "batt_temp_entity"
CONF_ODOMETER_ENTITY: Final = "odometer_entity"
CONF_RANGE_ENTITY: Final = "range_entity"
CONF_SOH_ENTITY: Final = "soh_entity"
CONF_VOLTAGE_ENTITY: Final = "voltage_entity"
CONF_CURRENT_ENTITY: Final = "current_entity"
CONF_HEADING_ENTITY: Final = "heading_entity"
CONF_ELEVATION_ENTITY: Final = "elevation_entity"

# Optional fixed values
CONF_SOH_FIXED: Final = "soh_fixed"
CONF_CAPACITY_FIXED: Final = "capacity_fixed"

DEFAULT_MIN_UPDATE_SECONDS: Final = 5
DEFAULT_MAX_STALE_SECONDS: Final = 30
DEFAULT_CAR_MODEL: Final = ""

# HA events fired by this integration
EVENT_TELEMETRY_SENT: Final = f"{DOMAIN}_telemetry_sent"
EVENT_TELEMETRY_ERROR: Final = f"{DOMAIN}_telemetry_error"

# Entity keys used when building tlm payloads
TLM_ENTITY_KEYS: Final = {
    CONF_SOC_ENTITY: "soc",
    CONF_SPEED_ENTITY: "speed",
    CONF_POWER_ENTITY: "power",
    CONF_CHARGING_ENTITY: "is_charging",
    CONF_DCFC_ENTITY: "is_dcfc",
    CONF_PARKED_ENTITY: "is_parked",
    CONF_EXT_TEMP_ENTITY: "ext_temp",
    CONF_BATT_TEMP_ENTITY: "batt_temp",
    CONF_ODOMETER_ENTITY: "odometer",
    CONF_RANGE_ENTITY: "est_battery_range",
    CONF_SOH_ENTITY: "soh",
    CONF_VOLTAGE_ENTITY: "voltage",
    CONF_CURRENT_ENTITY: "current",
    CONF_HEADING_ENTITY: "heading",
    CONF_ELEVATION_ENTITY: "elevation",
}

BOOLEAN_TLM_KEYS: Final = frozenset({"is_charging", "is_dcfc", "is_parked"})

ATTR_LAST_PAYLOAD: Final = "last_payload"
ATTR_LAST_SENT: Final = "last_sent"
ATTR_LAST_ERROR: Final = "last_error"
ATTR_TOTAL_SENT: Final = "total_sent"
ATTR_TOTAL_ERRORS: Final = "total_errors"
