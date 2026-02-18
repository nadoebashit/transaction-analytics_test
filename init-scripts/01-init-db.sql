-- Initialize database with extensions and optimizations
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create indexes for performance optimization
-- These will be created by Alembic migrations, but we ensure they exist

-- Set timezone
SET timezone = 'UTC';

-- Create application user with limited permissions (optional)
-- DO NOT USE IN PRODUCTION WITHOUT PROPER SECURITY REVIEW
-- CREATE USER app_user WITH PASSWORD 'app_password';
-- GRANT CONNECT ON DATABASE transaction_analytics TO app_user;
-- GRANT USAGE ON SCHEMA public TO app_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;
