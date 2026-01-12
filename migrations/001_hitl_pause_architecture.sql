-- HITL Pause Architecture - Database Migrations
-- Date: 2026-01-12
-- Purpose: Add WAITING_FOR_HUMAN status, domain-based sessions, domain learning

-- =============================================================================
-- 1. Add WAITING_FOR_HUMAN to RunStatus enum
-- =============================================================================

-- Check if value already exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum 
        WHERE enumlabel = 'waiting_for_human' 
        AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'runstatus')
    ) THEN
        ALTER TYPE runstatus ADD VALUE 'waiting_for_human';
    END IF;
END$$;

-- =============================================================================
-- 2. Update session_vaults table (domain-based, not job-based)
-- =============================================================================

-- Drop old job_id FK if exists
ALTER TABLE session_vaults DROP CONSTRAINT IF EXISTS session_vaults_job_id_fkey;

-- Add new columns
ALTER TABLE session_vaults 
    ADD COLUMN IF NOT EXISTS domain VARCHAR,
    ADD COLUMN IF NOT EXISTS captured_at TIMESTAMP DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS last_validated TIMESTAMP DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS expires_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS is_valid BOOLEAN DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS health_status VARCHAR DEFAULT 'valid',
    ADD COLUMN IF NOT EXISTS intervention_id UUID REFERENCES intervention_tasks(id),
    ADD COLUMN IF NOT EXISTS notes TEXT,
    ADD COLUMN IF NOT EXISTS validation_attempts JSONB DEFAULT '[]';

-- Migrate existing data (if any)
-- Extract domain from job.target_url for existing sessions
UPDATE session_vaults sv
SET domain = regexp_replace(
    regexp_replace(
        (SELECT target_url FROM jobs WHERE id = sv.job_id),
        '^https?://(www\.)?',
        ''
    ),
    '/.*$',
    ''
)
WHERE domain IS NULL AND job_id IS NOT NULL;

-- Now we can drop job_id (data migrated)
ALTER TABLE session_vaults DROP COLUMN IF EXISTS job_id;

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_sessions_domain ON session_vaults(domain);
CREATE INDEX IF NOT EXISTS idx_sessions_valid ON session_vaults(is_valid, health_status);
CREATE INDEX IF NOT EXISTS idx_sessions_intervention ON session_vaults(intervention_id) WHERE intervention_id IS NOT NULL;

-- =============================================================================
-- 3. Create domain_configs table (domain learning)
-- =============================================================================

CREATE TABLE IF NOT EXISTS domain_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain VARCHAR UNIQUE NOT NULL,
    
    -- Access classification
    access_class VARCHAR DEFAULT 'public', -- public/infra/human
    requires_session VARCHAR DEFAULT 'no', -- no/optional/required
    
    -- Success tracking
    total_attempts INTEGER DEFAULT 0,
    successful_attempts INTEGER DEFAULT 0,
    block_rate_403 FLOAT DEFAULT 0.0,
    block_rate_captcha FLOAT DEFAULT 0.0,
    
    -- Engine performance
    engine_stats JSONB DEFAULT '{}',
    -- Example: {"http": {"attempts": 10, "success": 2}, "playwright": {...}}
    
    -- Provider routing
    provider_preference VARCHAR,
    provider_success_rate FLOAT DEFAULT 0.0,
    
    -- Session management
    session_avg_lifetime_days FLOAT,
    last_session_refresh TIMESTAMP,
    
    -- Block patterns
    block_patterns JSONB DEFAULT '{}',
    -- Example: {"cloudflare": true, "recaptcha": true}
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_domain_config_domain ON domain_configs(domain);
CREATE INDEX IF NOT EXISTS idx_domain_config_access ON domain_configs(access_class);
CREATE INDEX IF NOT EXISTS idx_domain_config_block_rate ON domain_configs(block_rate_403);

-- =============================================================================
-- 4. Add intervention_id to runs table (for pause tracking)
-- =============================================================================

ALTER TABLE runs 
    ADD COLUMN IF NOT EXISTS intervention_id UUID REFERENCES intervention_tasks(id);

CREATE INDEX IF NOT EXISTS idx_runs_intervention ON runs(intervention_id) WHERE intervention_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_runs_waiting ON runs(status) WHERE status = 'waiting_for_human';

-- =============================================================================
-- 5. Seed initial domain configs for known domains
-- =============================================================================

INSERT INTO domain_configs (domain, access_class, requires_session, notes)
VALUES 
    ('www.fastpeoplesearch.com', 'human', 'required', 'People search - requires session after 403 blocks'),
    ('www.truepeoplesearch.com', 'human', 'required', 'People search - requires session after 403 blocks')
ON CONFLICT (domain) DO UPDATE SET
    access_class = EXCLUDED.access_class,
    requires_session = EXCLUDED.requires_session,
    notes = EXCLUDED.notes,
    updated_at = NOW();

-- =============================================================================
-- DONE
-- =============================================================================

-- Verify changes
SELECT 
    'session_vaults columns' as check_type,
    column_name,
    data_type
FROM information_schema.columns
WHERE table_name = 'session_vaults'
    AND column_name IN ('domain', 'health_status', 'last_validated', 'intervention_id')
ORDER BY column_name;

SELECT 
    'domain_configs table' as check_type,
    COUNT(*) as row_count
FROM domain_configs;

SELECT 
    'waiting_for_human enum' as check_type,
    enumlabel
FROM pg_enum
WHERE enumlabel = 'waiting_for_human'
    AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'runstatus');

-- Success message
SELECT '✅ HITL Pause Architecture migrations complete!' as status;
