-- Main tables for entity data
CREATE TABLE IF NOT EXISTS guilds (
    id BIGINT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_active TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS users (
    id BIGINT PRIMARY KEY,
    username VARCHAR(100),
    discriminator VARCHAR(4),
    first_seen TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_active TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Specialized table for prefixes
CREATE TABLE IF NOT EXISTS prefixes (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(10) NOT NULL, -- 'guild' or 'user'
    entity_id BIGINT NOT NULL,
    prefix VARCHAR(10) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(entity_type, entity_id)
);

-- Index for faster lookups
CREATE INDEX IF NOT EXISTS idx_prefixes_lookup ON prefixes(entity_type, entity_id);