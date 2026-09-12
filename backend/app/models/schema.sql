CREATE TABLE organizations (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    organization_type VARCHAR(32) NOT NULL CHECK (organization_type IN ('manufacturer', 'logistics', 'admin')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE users (
    id UUID PRIMARY KEY,
    organization_id UUID NOT NULL REFERENCES organizations(id),
    email VARCHAR(320) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role VARCHAR(32) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE product_units (
    id UUID PRIMARY KEY,
    serial_number VARCHAR(255) NOT NULL UNIQUE,
    qr_public_token VARCHAR(255) NOT NULL UNIQUE,
    gtin VARCHAR(14),
    batch_number VARCHAR(255) NOT NULL,
    expiry_date DATE NOT NULL,
    organization_id UUID NOT NULL REFERENCES organizations(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE lifecycle_events (
    id UUID PRIMARY KEY,
    product_unit_id UUID NOT NULL REFERENCES product_units(id),
    actor_id UUID REFERENCES users(id),
    event_type VARCHAR(64) NOT NULL,
    location VARCHAR(255),
    occurred_at TIMESTAMPTZ NOT NULL,
    event_hash VARCHAR(128) NOT NULL,
    previous_event_hash VARCHAR(128),
    transaction_hash VARCHAR(128),
    chain_status VARCHAR(32) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE verification_events (
    id UUID PRIMARY KEY,
    product_unit_id UUID NOT NULL REFERENCES product_units(id),
    verified_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ip_address INET,
    is_duplicate BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE provenance_flags (
    id UUID PRIMARY KEY,
    event_id UUID NOT NULL REFERENCES lifecycle_events(id),
    risk_score NUMERIC(5, 2) NOT NULL CHECK (risk_score >= 0 AND risk_score <= 100),
    risk_level VARCHAR(16) NOT NULL,
    reason TEXT NOT NULL,
    feature_values JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE iot_devices (
    id UUID PRIMARY KEY,
    device_uid VARCHAR(255) NOT NULL UNIQUE,
    product_unit_id UUID REFERENCES product_units(id),
    device_status VARCHAR(32) NOT NULL DEFAULT 'active',
    last_seen_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE iot_readings (
    id UUID PRIMARY KEY,
    device_id UUID REFERENCES iot_devices(id),
    product_unit_id UUID REFERENCES product_units(id),
    recorded_at TIMESTAMPTZ NOT NULL,
    temperature NUMERIC(8, 3) NOT NULL,
    humidity NUMERIC(8, 3) NOT NULL,
    accel_x NUMERIC(10, 5) NOT NULL,
    accel_y NUMERIC(10, 5) NOT NULL,
    accel_z NUMERIC(10, 5) NOT NULL,
    accel_magnitude NUMERIC(10, 5) NOT NULL
);