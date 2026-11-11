-- Schema for PostgreSQL / Neon
CREATE TABLE IF NOT EXISTS upload_sessions (
    session_id UUID PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS transactions (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES upload_sessions(session_id) ON DELETE CASCADE,
    transaction_date TIMESTAMP WITH TIME ZONE NOT NULL,
    merchant TEXT NOT NULL,
    category TEXT NOT NULL,
    description TEXT,
    amount NUMERIC(12, 2) NOT NULL,
    type VARCHAR(20) NOT NULL,
    extra_data JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_transactions_session_id ON transactions(session_id);
CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(session_id, transaction_date);
CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(session_id, category);
CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(session_id, type);
CREATE INDEX IF NOT EXISTS idx_upload_sessions_expires ON upload_sessions(expires_at);
