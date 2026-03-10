-- Session share links (snapshot at creation time — immutable)
CREATE TABLE IF NOT EXISTS session_shares (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token VARCHAR(64) UNIQUE NOT NULL,   -- secrets.token_urlsafe(32) = 43 chars
    created_by UUID REFERENCES profiles(id),
    expires_at TIMESTAMPTZ NOT NULL DEFAULT NOW() + INTERVAL '7 days',
    viewed_at TIMESTAMPTZ,               -- set on first non-crawler GET
    claimed_at TIMESTAMPTZ,              -- set when prospect claims after signup
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Snapshot captured at creation time (never updated)
    snapshot_robot_id TEXT NOT NULL,
    snapshot_robot_name TEXT NOT NULL,
    snapshot_monthly_lease NUMERIC NOT NULL,
    snapshot_monthly_savings NUMERIC,
    snapshot_hours_saved NUMERIC,
    snapshot_company_name TEXT,
    snapshot_answers JSONB
);

CREATE INDEX IF NOT EXISTS idx_session_shares_token ON session_shares(token);

ALTER TABLE session_shares ENABLE ROW LEVEL SECURITY;

-- Admins (authenticated users) can insert their own shares
CREATE POLICY "Admin can create shares"
    ON session_shares FOR INSERT
    WITH CHECK (
        created_by = (SELECT id FROM profiles WHERE user_id = auth.uid())
    );

-- Backend service role handles public reads (no direct anon access)
CREATE POLICY "Service role has full access to session_shares"
    ON session_shares FOR ALL
    USING (auth.role() = 'service_role');
