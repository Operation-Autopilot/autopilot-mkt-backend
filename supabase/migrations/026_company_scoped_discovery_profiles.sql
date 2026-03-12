-- Make discovery profiles company-scoped
-- Discovery answers describe the company/facility, not individual users.
-- All company members should share the same discovery data.

-- Step 1: Add company_id column (nullable for solo users)
ALTER TABLE discovery_profiles
ADD COLUMN company_id UUID REFERENCES companies(id) ON DELETE SET NULL;

-- Step 2: Drop the existing UNIQUE constraint on profile_id
-- (allows company-level lookup instead of per-user only)
ALTER TABLE discovery_profiles DROP CONSTRAINT discovery_profiles_profile_id_key;

-- Step 3: One discovery profile per company (partial unique index)
CREATE UNIQUE INDEX idx_discovery_profiles_company_id
ON discovery_profiles(company_id) WHERE company_id IS NOT NULL;

-- Step 4: Solo users (no company) still get one profile per user
CREATE UNIQUE INDEX idx_discovery_profiles_profile_id_no_company
ON discovery_profiles(profile_id) WHERE company_id IS NULL;

-- Step 5: Index for company_id lookups
CREATE INDEX IF NOT EXISTS idx_discovery_profiles_company_id_lookup
ON discovery_profiles(company_id) WHERE company_id IS NOT NULL;

-- Step 6: Backfill - link existing discovery profiles to their owner's company
UPDATE discovery_profiles dp
SET company_id = cm.company_id
FROM company_members cm
WHERE cm.profile_id = dp.profile_id
  AND cm.role = 'owner';

-- Step 7: RLS policies for company member access
CREATE POLICY "Company members can view company discovery profile"
    ON discovery_profiles FOR SELECT
    USING (
        company_id IS NOT NULL
        AND EXISTS (
            SELECT 1 FROM company_members cm
            JOIN profiles p ON cm.profile_id = p.id
            WHERE cm.company_id = discovery_profiles.company_id
            AND p.user_id = auth.uid()
        )
    );

CREATE POLICY "Company members can update company discovery profile"
    ON discovery_profiles FOR UPDATE
    USING (
        company_id IS NOT NULL
        AND EXISTS (
            SELECT 1 FROM company_members cm
            JOIN profiles p ON cm.profile_id = p.id
            WHERE cm.company_id = discovery_profiles.company_id
            AND p.user_id = auth.uid()
        )
    );
