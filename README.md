# ABRP Push for Home Assistant

Custom integration that **subscribes to Home Assistant state-change events** and pushes live EV telemetry to [A Better Routeplanner (ABRP)](https://abetterrouteplanner.com/) via the Iternio Telemetry API.

Unlike poll-every-N-seconds approaches, this integration reacts when mapped sensors change, rate-limits pushes, and optionally sends a quiet-period heartbeat so ABRP still receives calibration data.

## Features

- Event-driven updates via `async_track_state_change_event`
- Multiple cars: add the integration once per vehicle (shared API key, unique user token)
- Proper ABRP auth: `Authorization: APIKEY <telemetry_api_key>` + per-vehicle user token in the JSON body
- Configurable minimum push interval and stale heartbeat
- Upload on/off switch per vehicle
- Status sensor with last payload / error attributes
- Domain events: `abrp_push_telemetry_sent`, `abrp_push_telemetry_error`
- Service: `abrp_push.push_now`

## Prerequisites

1. **Telemetry API key** — generate a free key at [abetterrouteplanner.com/resources/api](https://abetterrouteplanner.com/resources/api) (Manage your telemetry API keys), or email contact@iternio.com.
2. **User token per vehicle** — in the ABRP app: Settings → Car → Live Data / Generic → Show token (or Link Generic).

## Installation

### Manual

1. Copy `custom_components/abrp_push` into your Home Assistant `config/custom_components/` folder.
2. Restart Home Assistant.
3. Settings → Devices & Services → Add Integration → **ABRP Push**.

### HACS (custom repository)

1. HACS → Integrations → ⋮ → Custom repositories
2. URL: `https://github.com/samhunt/hass-abrp-push`
3. Category: Integration
4. Download **ABRP Push**, then restart Home Assistant

## Setup

1. Enter a vehicle name, your telemetry API key, and that vehicle’s user token.
2. Optionally set an ABRP `car_model` code and push intervals.
3. Map at least a **SOC** sensor. Map speed, power, position, charging, etc. as available.
4. Repeat Add Integration for each additional car (new user token).

### Intervals

| Setting | Default | Meaning |
| --- | --- | --- |
| Minimum seconds between pushes | 5 | Coalesces rapid sensor changes |
| Heartbeat when quiet | 30 | Re-sends current snapshot if nothing changed (0 disables) |

ABRP recommends roughly once per 5–10 seconds while driving for consumption calibration.

## Events

```yaml
alias: ABRP push failed
trigger:
  - platform: event
    event_type: abrp_push_telemetry_error
action:
  - service: notify.persistent_notification
    data:
      message: "{{ trigger.event.data.vehicle }}: {{ trigger.event.data.error }}"
```

Successful pushes fire `abrp_push_telemetry_sent` with `vehicle`, `reason`, and `tlm`.

## Service

```yaml
service: abrp_push.push_now
data:
  vehicle: "My EV"
```

## API details

- Endpoint: `POST https://api.iternio.com/1/tlm/send`
- Header: `Authorization: APIKEY <api_key>`
- Body: `{"token": "<user_token>", "tlm": { ... }}`

Units follow the [Iternio Telemetry API](https://documenter.getpostman.com/view/7396339/SWTK5a8w): SOC %, speed km/h, power kW (discharge positive / charge negative), lat/lon degrees, etc.

## License

MIT
