-- Add functional role column to invitations table
-- This stores the role assigned by the inviter (e.g. Finance, Facilities, VP Ops)
-- so the accepted member gets that role in company_members instead of generic "member"
ALTER TABLE invitations ADD COLUMN IF NOT EXISTS role VARCHAR(50) NOT NULL DEFAULT 'Other';
