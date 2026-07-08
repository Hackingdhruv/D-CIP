-- Runs once on first database initialization (docker-entrypoint-initdb.d).
-- Enables extensions the platform relies on. No application tables are created
-- here — schema is owned by Alembic migrations.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";   -- UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";    -- gen_random_uuid(), digests
CREATE EXTENSION IF NOT EXISTS "pg_trgm";     -- trigram search for fuzzy lookups
