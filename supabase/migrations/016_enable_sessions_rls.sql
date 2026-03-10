-- Enable RLS on sessions table to protect sensitive session_token column
-- Backend access via service role key (sb_secret_) bypasses RLS automatically
-- No permissive policies needed - all access goes through the backend service

ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
