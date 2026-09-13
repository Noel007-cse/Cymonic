-- ============================================================
-- Supabase Schema for Real Estate Lead Qualifier
-- Run this in: Supabase Dashboard → SQL Editor
-- ============================================================

-- ── Properties table ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS properties (
    property_id     TEXT PRIMARY KEY,
    property_name   TEXT NOT NULL,
    property_type   TEXT,
    location        TEXT,
    price           BIGINT DEFAULT 0,
    bedrooms        INT DEFAULT 0,
    bathrooms       INT DEFAULT 0,
    area_sqft       INT DEFAULT 0,
    parking         TEXT,
    furnishing      TEXT,
    floor           INT,
    total_floors    INT,
    property_age    INT,
    possession      TEXT,
    amenities       TEXT,
    description     TEXT,
    availability    TEXT DEFAULT 'Available',
    broker_name     TEXT DEFAULT '',
    broker_phone    TEXT DEFAULT '',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── Buyers / Leads table ─────────────────────────────────────
CREATE TABLE IF NOT EXISTS buyers (
    buyer_id            TEXT PRIMARY KEY,
    name                TEXT,
    phone               TEXT,
    email               TEXT,
    budget              BIGINT DEFAULT 0,
    budget_min          BIGINT DEFAULT 0,
    budget_max          BIGINT DEFAULT 0,
    location            TEXT,
    property_type       TEXT,
    bedrooms            INT DEFAULT 0,
    timeline            TEXT,
    timeline_days       INT DEFAULT 0,
    purpose             TEXT,
    parking             TEXT,
    size_min_sqft       INT DEFAULT 0,
    size_max_sqft       INT DEFAULT 0,
    financing           TEXT,
    amenities           TEXT,
    qualification_score INT DEFAULT 0,
    status              TEXT DEFAULT 'NEW',
    priority            TEXT DEFAULT 'LOW',
    best_match_property TEXT,
    best_match_score    FLOAT DEFAULT 0,
    next_action         TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

-- ── Row Level Security (disable for now, enable per your auth needs) ──
ALTER TABLE properties ENABLE ROW LEVEL SECURITY;
ALTER TABLE buyers ENABLE ROW LEVEL SECURITY;

-- Allow anonymous read/write (for this app with anon key)
CREATE POLICY "Allow anon read properties"  ON properties FOR SELECT USING (true);
CREATE POLICY "Allow anon insert properties" ON properties FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow anon update properties" ON properties FOR UPDATE USING (true);

CREATE POLICY "Allow anon read buyers"   ON buyers FOR SELECT USING (true);
CREATE POLICY "Allow anon insert buyers" ON buyers FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow anon update buyers" ON buyers FOR UPDATE USING (true);
CREATE POLICY "Allow anon delete buyers" ON buyers FOR DELETE USING (true);
