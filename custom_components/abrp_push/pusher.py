"""Event-driven ABRP telemetry pusher."""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any

from homeassistant.const import (
    ATTR_UNIT_OF_MEASUREMENT,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_call_later, async_track_state_change_event
from homeassistant.util import dt as dt_util

from .api import AbrpApiClient, AbrpApiError
from .const import (
    ATTR_LAST_ERROR,
    ATTR_LAST_PAYLOAD,
    ATTR_LAST_SENT,
    ATTR_TOTAL_ERRORS,
    ATTR_TOTAL_SENT,
    BOOLEAN_TLM_KEYS,
    CONF_API_KEY,
    CONF_CAPACITY_FIXED,
    CONF_CAR_MODEL,
    CONF_CHARGING_ENTITY,
    CONF_LATITUDE_ENTITY,
    CONF_LONGITUDE_ENTITY,
    CONF_MAX_STALE_SECONDS,
    CONF_MIN_UPDATE_SECONDS,
    CONF_POSITION_ENTITY,
    CONF_POWER_ENTITY,
    CONF_SOH_FIXED,
    CONF_USER_TOKEN,
    CONF_VEHICLE_NAME,
    DEFAULT_CAR_MODEL,
    DEFAULT_MAX_STALE_SECONDS,
    DEFAULT_MIN_UPDATE_SECONDS,
    EVENT_TELEMETRY_ERROR,
    EVENT_TELEMETRY_SENT,
    TLM_ENTITY_KEYS,
)

_LOGGER = logging.getLogger(__name__)

_TRUE_STATES = frozenset({"on", "true", "yes", "1", "charging", "dc", "parked", "p"})


class AbrpPusher:
    """Subscribe to Home Assistant state-change events and push to ABRP."""

    def __init__(self, hass: HomeAssistant, data: dict[str, Any], options: dict[str, Any]) -> None:
        self.hass = hass
        self._data = data
        self._options = options
        self._client: AbrpApiClient | None = None
        self._unsub_state: CALLBACK_TYPE | None = None
        self._unsub_debounce: CALLBACK_TYPE | None = None
        self._unsub_stale: CALLBACK_TYPE | None = None
        self._enabled = True
        self._pending = False
        self._send_lock = False
        self._last_send_monotonic = 0.0
        self._last_payload: dict[str, Any] | None = None
        self._last_sent: datetime | None = None
        self._last_error: str | None = None
        self._total_sent = 0
        self._total_errors = 0
        self._listeners: list[CALLBACK_TYPE] = []

    @property
    def vehicle_name(self) -> str:
        return self._data.get(CONF_VEHICLE_NAME, "ABRP Vehicle")

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def status_attrs(self) -> dict[str, Any]:
        return {
            ATTR_LAST_PAYLOAD: self._last_payload,
            ATTR_LAST_SENT: self._last_sent.isoformat() if self._last_sent else None,
            ATTR_LAST_ERROR: self._last_error,
            ATTR_TOTAL_SENT: self._total_sent,
            ATTR_TOTAL_ERRORS: self._total_errors,
            "enabled": self._enabled,
            "watched_entities": self._watched_entities(),
        }

    def async_add_listener(self, update_callback: CALLBACK_TYPE) -> CALLBACK_TYPE:
        """Register a listener for status updates; return unsubscribe."""
        self._listeners.append(update_callback)

        @callback
        def _remove() -> None:
            if update_callback in self._listeners:
                self._listeners.remove(update_callback)

        return _remove

    @callback
    def _notify_listeners(self) -> None:
        for listener in list(self._listeners):
            listener()

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        _LOGGER.info("ABRP push %s for %s", "enabled" if enabled else "disabled", self.vehicle_name)
        if enabled:
            self._schedule_push(reason="enabled")
            self._arm_stale_timer()
        else:
            self._cancel_debounce()
            self._cancel_stale()
        self._notify_listeners()

    def update_config(self, data: dict[str, Any], options: dict[str, Any]) -> None:
        """Apply updated config/options and rebind listeners."""
        self._data = data
        self._options = options
        if self._client is not None:
            self._client = AbrpApiClient(
                async_get_clientsession(self.hass),
                data[CONF_API_KEY],
                data[CONF_USER_TOKEN],
            )
        self._bind_state_listener()
        self._arm_stale_timer()
        self._notify_listeners()

    async def async_start(self) -> None:
        """Start watching entities and push an initial snapshot."""
        session = async_get_clientsession(self.hass)
        self._client = AbrpApiClient(
            session,
            self._data[CONF_API_KEY],
            self._data[CONF_USER_TOKEN],
        )
        self._bind_state_listener()
        self._arm_stale_timer()
        await self.async_push_now(reason="startup")
        _LOGGER.info(
            "ABRP push started for %s (watching %s entities)",
            self.vehicle_name,
            len(self._watched_entities()),
        )

    async def async_stop(self) -> None:
        """Stop listeners and timers."""
        self._cancel_debounce()
        self._cancel_stale()
        if self._unsub_state is not None:
            self._unsub_state()
            self._unsub_state = None
        self._listeners.clear()
        self._client = None

    def _min_interval(self) -> float:
        return float(
            self._options.get(
                CONF_MIN_UPDATE_SECONDS,
                self._data.get(CONF_MIN_UPDATE_SECONDS, DEFAULT_MIN_UPDATE_SECONDS),
            )
        )

    def _max_stale(self) -> float:
        return float(
            self._options.get(
                CONF_MAX_STALE_SECONDS,
                self._data.get(CONF_MAX_STALE_SECONDS, DEFAULT_MAX_STALE_SECONDS),
            )
        )

    def _watched_entities(self) -> list[str]:
        entities: list[str] = []
        for conf_key in TLM_ENTITY_KEYS:
            entity_id = self._options.get(conf_key) or self._data.get(conf_key)
            if entity_id:
                entities.append(entity_id)

        position = self._options.get(CONF_POSITION_ENTITY) or self._data.get(CONF_POSITION_ENTITY)
        if position:
            entities.append(position)

        for conf_key in (CONF_LATITUDE_ENTITY, CONF_LONGITUDE_ENTITY):
            entity_id = self._options.get(conf_key) or self._data.get(conf_key)
            if entity_id:
                entities.append(entity_id)

        # Preserve order, drop duplicates
        seen: set[str] = set()
        unique: list[str] = []
        for entity_id in entities:
            if entity_id not in seen:
                seen.add(entity_id)
                unique.append(entity_id)
        return unique

    def _bind_state_listener(self) -> None:
        if self._unsub_state is not None:
            self._unsub_state()
            self._unsub_state = None

        entities = self._watched_entities()
        if not entities:
            _LOGGER.warning(
                "ABRP push for %s has no mapped entities; nothing to subscribe to",
                self.vehicle_name,
            )
            return

        self._unsub_state = async_track_state_change_event(
            self.hass,
            entities,
            self._async_on_state_change,
        )

    @callback
    def _async_on_state_change(self, event: Event) -> None:
        """Handle a watched entity state-changed event."""
        if not self._enabled:
            return

        new_state = event.data.get("new_state")
        old_state = event.data.get("old_state")
        if new_state is None:
            return
        if old_state is not None and old_state.state == new_state.state:
            # Attribute-only changes (e.g. device_tracker lat/lon) still matter
            if old_state.attributes == new_state.attributes:
                return

        entity_id = event.data.get("entity_id")
        _LOGGER.debug(
            "ABRP push %s: state change on %s -> scheduling send",
            self.vehicle_name,
            entity_id,
        )
        self._schedule_push(reason="state_change")

    @callback
    def _schedule_push(self, *, reason: str) -> None:
        """Debounce / rate-limit pushes after a change."""
        if not self._enabled:
            return

        self._pending = True
        elapsed = time.monotonic() - self._last_send_monotonic
        min_interval = self._min_interval()
        delay = 0.0 if elapsed >= min_interval else (min_interval - elapsed)

        self._cancel_debounce()

        @callback
        def _fire(_now: datetime) -> None:
            self._unsub_debounce = None
            self.hass.async_create_task(self.async_push_now(reason=reason))

        self._unsub_debounce = async_call_later(self.hass, delay, _fire)

    def _cancel_debounce(self) -> None:
        if self._unsub_debounce is not None:
            self._unsub_debounce()
            self._unsub_debounce = None

    def _cancel_stale(self) -> None:
        if self._unsub_stale is not None:
            self._unsub_stale()
            self._unsub_stale = None

    def _arm_stale_timer(self) -> None:
        """Re-arm heartbeat so ABRP still gets data when sensors are quiet."""
        self._cancel_stale()
        if not self._enabled:
            return

        stale = self._max_stale()
        if stale <= 0:
            return

        @callback
        def _stale(_now: datetime) -> None:
            self._unsub_stale = None
            if self._enabled:
                self.hass.async_create_task(self.async_push_now(reason="stale_heartbeat"))

        self._unsub_stale = async_call_later(self.hass, stale, _stale)

    async def async_push_now(self, *, reason: str = "manual") -> bool:
        """Build current telemetry and send it immediately."""
        if not self._enabled:
            return False
        if self._client is None:
            return False
        if self._send_lock:
            self._pending = True
            return False

        self._send_lock = True
        self._pending = False
        try:
            tlm = self._build_tlm()
            if "soc" not in tlm:
                _LOGGER.debug(
                    "ABRP push %s skipped (%s): SOC unavailable",
                    self.vehicle_name,
                    reason,
                )
                return False

            await self._client.async_send_telemetry(tlm)
            self._last_send_monotonic = time.monotonic()
            self._last_payload = tlm
            self._last_sent = dt_util.utcnow()
            self._last_error = None
            self._total_sent += 1

            self.hass.bus.async_fire(
                EVENT_TELEMETRY_SENT,
                {
                    "vehicle": self.vehicle_name,
                    "reason": reason,
                    "tlm": tlm,
                },
            )
            _LOGGER.debug("ABRP push %s sent (%s): %s", self.vehicle_name, reason, tlm)
            return True
        except AbrpApiError as err:
            self._last_error = str(err)
            self._total_errors += 1
            self.hass.bus.async_fire(
                EVENT_TELEMETRY_ERROR,
                {
                    "vehicle": self.vehicle_name,
                    "reason": reason,
                    "error": str(err),
                    "status": err.status,
                },
            )
            _LOGGER.warning("ABRP push %s failed (%s): %s", self.vehicle_name, reason, err)
            return False
        finally:
            self._send_lock = False
            self._arm_stale_timer()
            self._notify_listeners()
            if self._pending:
                self._schedule_push(reason="coalesced")

    def _build_tlm(self) -> dict[str, Any]:
        tlm: dict[str, Any] = {"utc": int(time.time())}

        for conf_key, tlm_key in TLM_ENTITY_KEYS.items():
            # Power is normalized separately (units + charging sign).
            if conf_key == CONF_POWER_ENTITY:
                continue
            entity_id = self._options.get(conf_key) or self._data.get(conf_key)
            if not entity_id:
                continue
            value = self._read_entity(entity_id, boolean=tlm_key in BOOLEAN_TLM_KEYS)
            if value is not None:
                tlm[tlm_key] = value

        power = self._read_power_kw(is_charging=bool(tlm.get("is_charging")))
        if power is not None:
            tlm["power"] = power

        lat, lon = self._read_position()
        if lat is not None:
            tlm["lat"] = lat
        if lon is not None:
            tlm["lon"] = lon

        car_model = self._options.get(CONF_CAR_MODEL) or self._data.get(
            CONF_CAR_MODEL, DEFAULT_CAR_MODEL
        )
        if car_model:
            tlm["car_model"] = car_model

        soh_fixed = self._options.get(CONF_SOH_FIXED, self._data.get(CONF_SOH_FIXED))
        if soh_fixed and "soh" not in tlm:
            tlm["soh"] = float(soh_fixed)

        capacity = self._options.get(CONF_CAPACITY_FIXED, self._data.get(CONF_CAPACITY_FIXED))
        if capacity:
            tlm["capacity"] = float(capacity)

        return tlm

    def _read_power_kw(self, *, is_charging: bool) -> float | None:
        """Read power as kW with ABRP sign: discharge +, charge -."""
        entity_id = self._options.get(CONF_POWER_ENTITY) or self._data.get(
            CONF_POWER_ENTITY
        )
        if not entity_id:
            return None

        state = self.hass.states.get(entity_id)
        if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN, None, ""):
            return None

        try:
            raw = float(state.state)
        except (TypeError, ValueError):
            return None

        unit = str(state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) or "").strip()
        power_kw = self._power_to_kw(raw, unit)

        charging_entity = self._options.get(CONF_CHARGING_ENTITY) or self._data.get(
            CONF_CHARGING_ENTITY
        )
        if charging_entity is not None:
            # Prefer charging entity when mapped: magnitude from sensor, sign from charge state.
            magnitude = abs(power_kw)
            return -magnitude if is_charging else magnitude

        # No charging sensor: keep the source sensor's sign after unit conversion.
        return power_kw

    @staticmethod
    def _power_to_kw(value: float, unit: str) -> float:
        """Convert a power reading to kilowatts using the sensor unit."""
        normalized = unit.strip().lower().replace(" ", "")

        if normalized in {"", "kw", "kilowatt", "kilowatts"}:
            return value
        if normalized in {"w", "watt", "watts"}:
            return value * 0.001
        if normalized in {"mw", "milliwatt", "milliwatts"}:
            # Prefer milliwatts for ambiguous "mw" (EV sensors never report megawatts).
            return value * 0.000001
        if normalized in {"megawatt", "megawatts"} or unit.strip() == "MW":
            return value * 1000.0

        _LOGGER.debug(
            "Unknown power unit %r on sensor; assuming kilowatts", unit or None
        )
        return value

    def _read_position(self) -> tuple[float | None, float | None]:
        position = self._options.get(CONF_POSITION_ENTITY) or self._data.get(CONF_POSITION_ENTITY)
        if position:
            state = self.hass.states.get(position)
            if state and state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN, None):
                lat = state.attributes.get("latitude")
                lon = state.attributes.get("longitude")
                try:
                    return (
                        float(lat) if lat is not None else None,
                        float(lon) if lon is not None else None,
                    )
                except (TypeError, ValueError):
                    pass

        lat_entity = self._options.get(CONF_LATITUDE_ENTITY) or self._data.get(CONF_LATITUDE_ENTITY)
        lon_entity = self._options.get(CONF_LONGITUDE_ENTITY) or self._data.get(
            CONF_LONGITUDE_ENTITY
        )
        lat_val = self._read_entity(lat_entity) if lat_entity else None
        lon_val = self._read_entity(lon_entity) if lon_entity else None
        return lat_val, lon_val

    def _read_entity(self, entity_id: str | None, *, boolean: bool = False) -> Any | None:
        if not entity_id:
            return None
        state = self.hass.states.get(entity_id)
        if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN, None, ""):
            return None

        raw = state.state
        if boolean:
            return 1 if str(raw).strip().lower() in _TRUE_STATES else 0

        try:
            return float(raw)
        except (TypeError, ValueError):
            # Binary sensors mapped to non-boolean tlm keys fall through
            if str(raw).strip().lower() in _TRUE_STATES:
                return 1
            if str(raw).strip().lower() in {"off", "false", "no", "0"}:
                return 0
            return None
