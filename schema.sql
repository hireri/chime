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

CREATE TABLE IF NOT EXISTS tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    name TEXT NOT NULL,
    content TEXT NOT NULL,
    user_id BIGINT NOT NULL,
    guild_id BIGINT NOT NULL,
    uses INT NOT NULL DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT unique_name_guild UNIQUE (name, guild_id)
);

CREATE INDEX IF NOT EXISTS idx_tags_name_guild ON tags (name, guild_id);

CREATE TABLE IF NOT EXISTS afk_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    user_id BIGINT NOT NULL,
    guild_id BIGINT NOT NULL,
    message TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (guild_id) REFERENCES guilds(id) ON DELETE CASCADE,
    CONSTRAINT unique_user_guild UNIQUE (user_id, guild_id)
);

CREATE INDEX IF NOT EXISTS idx_afk_users_user_guild ON afk_users (user_id, guild_id);

CREATE TABLE IF NOT EXISTS aliases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid (),
    created_at TIMESTAMPTZ DEFAULT now(),
    guild_id BIGINT NOT NULL,
    alias TEXT NOT NULL CHECK (alias = LOWER(alias)),
    command TEXT [] NOT NULL,
    CONSTRAINT unique_alias UNIQUE (alias),
    CONSTRAINT unique_guild_alias UNIQUE (guild_id, alias),
    FOREIGN KEY (guild_id) REFERENCES guilds(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_aliases_guild ON aliases (guild_id);