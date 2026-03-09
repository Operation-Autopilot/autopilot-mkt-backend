-- Migration: Add 3D model support to robot catalog
-- Adds fields to robot_catalog and creates robot_3d_models table

-- 1. Add 3D model fields to robot_catalog
ALTER TABLE robot_catalog
    ADD COLUMN model_glb_url TEXT,
    ADD COLUMN model_usdz_url TEXT,
    ADD COLUMN model_poster_url TEXT,
    ADD COLUMN has_3d_model BOOLEAN NOT NULL DEFAULT false;

-- 2. Create robot_3d_models table
CREATE TABLE robot_3d_models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    robot_id UUID NOT NULL REFERENCES robot_catalog(id),
    version INTEGER NOT NULL,
    source_image_urls TEXT[],
    pipeline_version VARCHAR(50),
    glb_url TEXT,
    usdz_url TEXT,
    glb_file_size_bytes INTEGER,
    vertex_count INTEGER,
    generation_params JSONB DEFAULT '{}',
    quality_score DECIMAL(3,2),
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    error_message TEXT,
    is_active BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (robot_id, version)
);

-- 3. Create index on robot_id for fast lookups
CREATE INDEX idx_robot_3d_models_robot_id ON robot_3d_models(robot_id);

-- 4. Enable RLS
ALTER TABLE robot_3d_models ENABLE ROW LEVEL SECURITY;

-- Public SELECT access
CREATE POLICY "Allow public read access on robot_3d_models"
    ON robot_3d_models
    FOR SELECT
    USING (true);

-- Service role full access (sb_secret_ key bypasses RLS, but explicit policy for clarity)
CREATE POLICY "Allow service role full access on robot_3d_models"
    ON robot_3d_models
    FOR ALL
    USING (true)
    WITH CHECK (true);

-- 5. Trigger function to auto-increment version per robot
CREATE OR REPLACE FUNCTION set_robot_3d_model_version()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.version IS NULL OR NEW.version = 0 THEN
        SELECT COALESCE(MAX(version), 0) + 1
        INTO NEW.version
        FROM robot_3d_models
        WHERE robot_id = NEW.robot_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_set_robot_3d_model_version
    BEFORE INSERT ON robot_3d_models
    FOR EACH ROW
    EXECUTE FUNCTION set_robot_3d_model_version();
