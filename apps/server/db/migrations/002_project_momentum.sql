-- Migration 002: Project Momentum tracking
-- Adds project momentum tracking for weekly audit and rewrite flows

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
CREATE INDEX IF NOT EXISTS idx_project_momentum_due ON project_momentum(due_date);

-- Create trigger to auto-update updated_at timestamp
CREATE TRIGGER IF NOT EXISTS update_project_momentum_timestamp
    AFTER UPDATE ON project_momentum
    FOR EACH ROW
BEGIN
    UPDATE project_momentum
    SET updated_at = CURRENT_TIMESTAMP
    WHERE project_id = NEW.project_id;
END;
