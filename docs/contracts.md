# SupplyChainX Interface Contracts

Frozen at Hour 2. All timestamps use ISO 8601 UTC strings. IDs are UUID strings
unless otherwise stated. JSON field names are `snake_case`.

## 1. Database Schema (Partner 1 owns this)

The following objects define the JSON shape used when a row is serialized by the
API. Database implementations may use native UUID, timestamp, numeric, and JSON
types, but the wire representation remains unchanged.

### `organizations`

```json
{
  "id": "org_01J8Q3Y5V7P6K2M4N8R0T1WXYZ",
  "name": "Acme Pharma",
  "organization_type": "manufacturer",
  "created_at": "2026-09-10T09:00:00Z"
}
```

`organization_type` is one of `manufacturer`, `logistics`, or `admin`.

### `users`

```json
{
  "id": "usr_01J8Q40B2Y7D6P9M3K5N8R1STU",
  "organization_id": "org_01J8Q3Y5V7P6K2M4N8R0T1WXYZ",
  "email": "operator@acme.example",
  "password_hash": "$argon2id$v=19$...",
  "role": "operator",
  "is_active": true,
  "created_at": "2026-09-10T09:05:00Z"
}
```

`role` is one of `admin`, `manager`, or `operator`. `password_hash` is never
returned by public API responses.

### `product_units`

```json
{
  "id": "unit_01J8Q45J9W3H7C2L6M8N0P4QRS",
  "serial_number": "ACME-2026-000001",
  "qr_public_token": "qr_pub_7f2c9a",
  "gtin": "08912345678901",
  "batch_number": "BATCH-2609-A",
  "expiry_date": "2028-09-30",
  "organization_id": "org_01J8Q3Y5V7P6K2M4N8R0T1WXYZ",
  "created_at": "2026-09-10T09:10:00Z"
}
```

### `lifecycle_events`

```json
{
  "id": "evt_01J8Q4B8N2S6D9F3G5H7J0KLMN",
  "product_unit_id": "unit_01J8Q45J9W3H7C2L6M8N0P4QRS",
  "actor_id": "usr_01J8Q40B2Y7D6P9M3K5N8R1STU",
  "event_type": "shipped",
  "location": "Delhi",
  "occurred_at": "2026-09-10T10:38:00Z",
  "event_hash": "0x8f0d...",
  "previous_event_hash": "0x2a91...",
  "transaction_hash": "0x4c72...",
  "chain_status": "pending",
  "created_at": "2026-09-10T10:38:02Z"
}
```

`chain_status` is one of `pending`, `confirmed`, or `failed`.

### `verification_events`

```json
{
  "id": "ver_01J8Q4H2R6T9V3X5Z7B0C1D2EF",
  "product_unit_id": "unit_01J8Q45J9W3H7C2L6M8N0P4QRS",
  "verified_at": "2026-09-10T14:00:00Z",
  "ip_address": "203.0.113.10",
  "is_duplicate": false
}
```

### `provenance_flags`

```json
{
  "id": "flag_01J8Q4M7Y2U6I9O3P5A8S0D1FG",
  "event_id": "evt_01J8Q4B8N2S6D9F3G5H7J0KLMN",
  "risk_score": 0.82,
  "risk_level": "high",
  "reason": "Temperature exceeded the configured cold-chain range.",
  "feature_values": {
    "temperature_max": 11.4,
    "location_jump_km": 842.7,
    "event_gap_minutes": 198
  },
  "created_at": "2026-09-10T14:00:03Z"
}
```

`risk_score` is a number from `0.0` to `1.0`. `risk_level` is one of `low`,
`medium`, or `high`.

### `iot_devices`

```json
{
  "id": "dev_01J8Q4R9E3W7T2Y6U8I0O5P4AS",
  "device_uid": "ARDUINO-UNO-001",
  "product_unit_id": "unit_01J8Q45J9W3H7C2L6M8N0P4QRS",
  "device_status": "active",
  "last_seen_at": "2026-09-10T14:00:00Z",
  "created_at": "2026-09-10T09:15:00Z"
}
```

`device_status` is one of `active`, `inactive`, or `retired`.

### `iot_readings`

```json
{
  "id": "reading_01J8Q4W1G5H9K3L7M0N2P6Q8RS",
  "device_id": "dev_01J8Q4R9E3W7T2Y6U8I0O5P4AS",
  "product_unit_id": "unit_01J8Q45J9W3H7C2L6M8N0P4QRS",
  "recorded_at": "2026-09-10T14:00:00Z",
  "temperature": 5.5,
  "humidity": 60.0,
  "accel_x": 0.1,
  "accel_y": 0.2,
  "accel_z": 0.9,
  "accel_magnitude": 0.93
}
```

---

## 2. AI Inference Contract (Partner 2 owns this)

### Input
```json
{
  "event_history": [
    {"event_type": "manufactured", "location": "Mumbai", "occurred_at": "2026-09-10T10:00:00Z"},
    {"event_type": "shipped", "location": "Delhi", "occurred_at": "2026-09-10T10:38:00Z"}
  ],
  "current_event": {
    "event_type": "received",
    "location": "Bangalore",
    "occurred_at": "2026-09-10T14:00:00Z"
  },
  "iot_readings": [
    {"temperature": 5.5, "humidity": 60.0, "accel_magnitude": 0.93, "recorded_at": "2026-09-10T13:59:58Z"}
  ]
}
```

`event_history` and `iot_readings` may be empty arrays. The inference service
must accept the fields shown above and may ignore additional fields.

### Output

```json
{
  "risk_score": 0.18,
  "risk_level": "low",
  "reason": "No significant anomaly detected.",
  "feature_values": {
    "temperature_max": 5.5,
    "humidity_max": 60.0,
    "accel_magnitude_max": 0.93,
    "event_gap_minutes": 198
  }
}
```

## 3. IoT Serial Format

Each line is UTF-8 text terminated by `\\n`:

```text
SCX|<device_uid>|<product_unit_id>|<temp>|<humidity>|<accel_x>|<accel_y>|<accel_z>|<accel_mag>
```

Example:

```text
SCX|ARDUINO-UNO-001|unit_01J8Q45J9W3H7C2L6M8N0P4QRS|5.50|60.00|0.10|0.20|0.90|0.93
```

The gateway must reject lines that do not contain exactly 9 pipe-delimited
fields or whose numeric fields cannot be parsed as numbers. The serial values
map to this API payload:

```json
{
  "device_uid": "ARDUINO-UNO-001",
  "product_unit_id": "unit_01J8Q45J9W3H7C2L6M8N0P4QRS",
  "temperature": 5.5,
  "humidity": 60.0,
  "accel_x": 0.1,
  "accel_y": 0.2,
  "accel_z": 0.9,
  "accel_magnitude": 0.93,
  "recorded_at": "2026-09-10T14:00:00Z"
}
```

## 4. Core REST API Endpoints

All endpoints are prefixed with `/api/v1`. Protected endpoints use
`Authorization: Bearer <access_token>`. Errors use `{ "detail": "<message>" }`.

| Method | Path | Request body | Response |
| --- | --- | --- | --- |
| `POST` | `/auth/register` | `{ "email", "password", "organization_id", "role" }` | `{ "user", "access_token", "token_type": "bearer" }` |
| `POST` | `/auth/login` | `{ "email", "password" }` | `{ "access_token", "token_type": "bearer" }` |
| `GET` | `/auth/me` | None | `{ "user" }` |
| `POST` | `/units` | Product unit without generated fields | `{ "unit" }` |
| `GET` | `/units` | Query: `skip`, `limit` | `{ "items": [], "total": 0 }` |
| `GET` | `/units/{unit_id}` | None | `{ "unit" }` |
| `POST` | `/units/{unit_id}/events` | Lifecycle event without generated fields | `{ "event", "provenance_flag": null }` |
| `GET` | `/units/{unit_id}/events` | Query: `skip`, `limit` | `{ "items": [], "total": 0 }` |
| `POST` | `/verify/{qr_public_token}` | None | `{ "unit", "events": [], "verification_event" }` |
| `POST` | `/iot/readings` | IoT API payload above | `{ "reading" }` |
| `GET` | `/iot/devices` | Query: `status` | `{ "items": [] }` |
| `GET` | `/iot/devices/{device_id}/readings` | Query: `from`, `to`, `limit` | `{ "items": [] }` |

The IoT gateway posts to `/iot/readings`; authentication for the hackathon
skeleton may be omitted, but the payload and response shape are frozen.