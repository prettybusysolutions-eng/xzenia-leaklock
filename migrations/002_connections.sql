-- OAuth connections table
CREATE TABLE IF NOT EXISTS saas_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform TEXT NOT NULL,
    user_email TEXT NOT NULL,
    access_token_enc TEXT NOT NULL,
    refresh_token_enc TEXT,
    token_expires_at TIMESTAMPTZ,
    realm_id TEXT,
    account_name TEXT,
    connected_at TIMESTAMPTZ DEFAULT NOW(),
    last_sync_at TIMESTAMPTZ,
    status TEXT DEFAULT 'active',
    UNIQUE(platform, user_email)
);

CREATE INDEX IF NOT EXISTS idx_connections_email ON saas_connections(user_email);
CREATE INDEX IF NOT EXISTS idx_connections_platform ON saas_connections(platform, status);
