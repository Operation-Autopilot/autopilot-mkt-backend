-- HubSpot OAuth connections (per-user, encrypted tokens)
CREATE TABLE IF NOT EXISTS hubspot_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id UUID REFERENCES profiles(id) ON DELETE CASCADE UNIQUE NOT NULL,
    access_token TEXT NOT NULL,   -- AES-256-GCM encrypted
    refresh_token TEXT,           -- AES-256-GCM encrypted
    expires_at TIMESTAMPTZ,
    hub_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_hubspot_connections_profile_id ON hubspot_connections(profile_id);

ALTER TABLE hubspot_connections ENABLE ROW LEVEL SECURITY;

-- Backend (service role) handles all access; no direct client access needed
CREATE POLICY "Service role has full access to hubspot_connections"
    ON hubspot_connections FOR ALL
    USING (auth.role() = 'service_role');

CREATE TRIGGER update_hubspot_connections_updated_at
    BEFORE UPDATE ON hubspot_connections
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
