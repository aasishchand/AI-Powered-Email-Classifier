-- Faculty Email Classification Platform - PostgreSQL init
-- Used for users, sessions, feedback; warehouse schema is Hive-compatible (see data-pipeline/sql/)

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users (faculty / admin)
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'faculty',
    department_id INT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Sessions / tokens (optional, if using DB-backed sessions)
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    token_hash VARCHAR(255),
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- User feedback for reclassified emails (for model retraining)
CREATE TABLE IF NOT EXISTS user_feedback (
    id BIGSERIAL PRIMARY KEY,
    message_id VARCHAR(512) NOT NULL,
    user_email VARCHAR(255) NOT NULL,
    original_label VARCHAR(50) NOT NULL,
    corrected_label VARCHAR(50) NOT NULL,
    reason TEXT,
    feedback_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_user_feedback_message_id ON user_feedback(message_id);
CREATE INDEX IF NOT EXISTS idx_user_feedback_user_email ON user_feedback(user_email);

-- Seed users: run email-api/scripts/seed_users.py after first boot to create admin/faculty with hashed passwords.
-- Or use /api/v1/auth/register to create users.
