-- Sprint 2 Migration: Add project momentum tracking
-- This migration adds the project_momentum table for tracking project activity and status

-- For PostgreSQL
-- CREATE TABLE IF NOT EXISTS project_momentum (
--     project_id TEXT PRIMARY KEY,
--     last_activity_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
--     momentum_score INTEGER DEFAULT 100,
--     status TEXT DEFAULT 'active',
--     outcome_defined BOOLEAN DEFAULT FALSE,
--     due_date DATE NULL,
--     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
--     updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
-- );

-- For SQLite (handled in engine.py init)
CREATE TABLE IF NOT EXISTS project_momentum (
    project_id TEXT PRIMARY KEY,
    last_activity_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    momentum_score INTEGER DEFAULT 100,
    status TEXT DEFAULT 'active',
    outcome_defined BOOLEAN DEFAULT FALSE,
    due_date DATE NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_project_momentum_status ON project_momentum(status);
CREATE INDEX IF NOT EXISTS idx_project_momentum_score ON project_momentum(momentum_score);
CREATE INDEX IF NOT EXISTS idx_project_momentum_activity ON project_momentum(last_activity_at);
