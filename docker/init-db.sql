-- Initialize PostgreSQL with required extensions

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable vector operations for embeddings
CREATE EXTENSION IF NOT EXISTS "vector";

-- Enable trigram for full-text search
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE ilmred TO postgres;
