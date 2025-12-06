# Database Integration Plan

## Overview

Fast local database to enhance the AI assistant with memory, knowledge retrieval, user preferences, and response caching.

## Technology Stack

- **PostgreSQL 16** with **pgvector** extension
- Docker container for easy deployment
- Python: `asyncpg` + `pgvector` libraries

### Why PostgreSQL + pgvector

- Single database handles all use cases
- Native vector embeddings for RAG/semantic search
- Reliable persistence for training data
- Good performance on RPi5 (8GB RAM is sufficient)
- Can add Redis later for caching if needed

## Database Schema

### 1. Conversations Table

Store chat history so AI remembers past interactions across sessions.

```sql
CREATE TABLE conversations (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL,  -- 'user' or 'assistant'
    content TEXT NOT NULL,
    language VARCHAR(10),
    intent VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);

CREATE INDEX idx_conversations_session ON conversations(session_id);
CREATE INDEX idx_conversations_created ON conversations(created_at);
```

### 2. Memory/Knowledge Table (RAG)

Store documents/facts for retrieval-augmented generation.

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE knowledge (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    embedding vector(384),  -- nomic-embed-text dimension
    source VARCHAR(255),
    tags TEXT[],
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_knowledge_embedding ON knowledge
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_knowledge_tags ON knowledge USING GIN(tags);
```

### 3. User Preferences Table

Store settings, learned behaviors, and personalization data.

```sql
CREATE TABLE preferences (
    id SERIAL PRIMARY KEY,
    key VARCHAR(255) UNIQUE NOT NULL,
    value JSONB NOT NULL,
    category VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Examples:
-- key: "entity_alias.my_office" -> value: {"entity_id": "light.office_main"}
-- key: "user.preferred_language" -> value: {"language": "pl"}
-- key: "user.wake_time" -> value: {"time": "07:00"}

CREATE INDEX idx_preferences_category ON preferences(category);
```

### 4. Response Cache Table

Cache common queries to speed up responses.

```sql
CREATE TABLE response_cache (
    id SERIAL PRIMARY KEY,
    query_hash VARCHAR(64) UNIQUE NOT NULL,
    query_text TEXT NOT NULL,
    response TEXT NOT NULL,
    hit_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    metadata JSONB
);

CREATE INDEX idx_cache_hash ON response_cache(query_hash);
CREATE INDEX idx_cache_expires ON response_cache(expires_at);
```

### 5. Training Data Table

Store successful interactions for fine-tuning and model improvement.

```sql
CREATE TABLE training_data (
    id SERIAL PRIMARY KEY,
    input_text TEXT NOT NULL,
    output_text TEXT NOT NULL,
    feedback_score INTEGER,  -- 1-5 rating
    interaction_type VARCHAR(50),  -- 'command', 'question', 'conversation'
    language VARCHAR(10),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    exported BOOLEAN DEFAULT FALSE,
    metadata JSONB
);

CREATE INDEX idx_training_feedback ON training_data(feedback_score);
CREATE INDEX idx_training_exported ON training_data(exported);
```

## Implementation Steps

### Step 1: Add PostgreSQL to Docker Compose

Add to `ai-gateway/docker-compose.yml`:

```yaml
services:
  postgres:
    image: pgvector/pgvector:pg16
    container_name: ai-postgres
    restart: unless-stopped
    environment:
      POSTGRES_USER: ai_assistant
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ai_assistant
    volumes:
      - /mnt/data-ssd/postgres-data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ai_assistant"]
      interval: 10s
      timeout: 5s
      retries: 5
```

### Step 2: Create Database Service Module

Create `ai-gateway/app/services/database.py`:

- Connection pooling with asyncpg
- CRUD operations for each table
- Vector similarity search
- Cache management with TTL

### Step 3: Add Embedding Generation

Create `ai-gateway/app/services/embeddings.py`:

- Use Ollama's `nomic-embed-text` model
- Generate 384-dimension embeddings
- Batch processing for efficiency

### Step 4: Integrate with Conversation Flow

Modify `ai-gateway/app/services/conversation_client.py`:

- Save conversations automatically after each turn
- Query relevant context from knowledge base
- Check cache before LLM call
- Learn from user corrections

### Step 5: Create Management Endpoints

Create `ai-gateway/app/routers/memory.py`:

```python
POST /memory/add        # Add knowledge entry
GET  /memory/search     # Semantic search
POST /preferences/set   # Update user preference
GET  /preferences/get   # Get preference value
POST /training/feedback # Record feedback score
GET  /training/export   # Export training data as JSONL
GET  /cache/stats       # Cache hit/miss statistics
DELETE /cache/clear     # Clear expired cache entries
```

## Files to Create/Modify

### New Files

- `ai-gateway/app/services/database.py` - Database client and operations
- `ai-gateway/app/services/embeddings.py` - Embedding generation
- `ai-gateway/app/routers/memory.py` - Memory management API
- `ai-gateway/app/models/database.py` - SQLAlchemy/Pydantic models
- `ai-gateway/migrations/001_initial_schema.sql` - Initial schema
- `ai-gateway/scripts/init_db.py` - Database initialization script

### Modified Files

- `ai-gateway/docker-compose.yml` - Add PostgreSQL service
- `ai-gateway/app/main.py` - Register new router, init DB pool
- `ai-gateway/app/services/conversation_client.py` - Add memory integration
- `ai-gateway/requirements.txt` - Add asyncpg, pgvector

## Resource Estimates

- **PostgreSQL**: ~200-500MB RAM
- **Storage**: Start with 1GB allocated, grows with usage
- **Embedding generation**: ~100-200ms per query (using Ollama)
- **Vector search**: <50ms for 10k entries

## Configuration

Environment variables to add:

```env
# Database
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=ai_assistant
POSTGRES_PASSWORD=<secure-password>
POSTGRES_DB=ai_assistant

# Embeddings
EMBEDDING_MODEL=nomic-embed-text
EMBEDDING_DIMENSIONS=384

# Cache
CACHE_TTL_SECONDS=3600
CACHE_MAX_ENTRIES=1000
```

## Usage Examples

### Adding Knowledge

```bash
curl -X POST http://localhost:8080/memory/add \
  -H "Content-Type: application/json" \
  -d '{
    "content": "The user prefers lights at 50% brightness in the evening",
    "tags": ["preference", "lighting"],
    "source": "user_feedback"
  }'
```

### Semantic Search

```bash
curl -X GET "http://localhost:8080/memory/search?query=lighting%20preferences&limit=5"
```

### Setting Preferences

```bash
curl -X POST http://localhost:8080/preferences/set \
  -H "Content-Type: application/json" \
  -d '{
    "key": "entity_alias.my_office",
    "value": {"entity_id": "light.office_main"},
    "category": "aliases"
  }'
```

### Recording Feedback

```bash
curl -X POST http://localhost:8080/training/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "interaction_id": "conv_123",
    "score": 5,
    "comment": "Correctly turned on all lights"
  }'
```

## Future Enhancements

1. **Redis caching layer** - Add for ultra-fast response caching if needed
2. **Automatic knowledge extraction** - Parse conversations for facts to store
3. **Forgetting mechanism** - Remove outdated or low-confidence memories
4. **Multi-user support** - Separate memories per user/profile
5. **Export to fine-tuning format** - Generate datasets for model training
6. **Backup automation** - Scheduled pg_dump to external storage

## Testing

```bash
# Test database connection
docker-compose exec postgres psql -U ai_assistant -c "SELECT 1"

# Test vector extension
docker-compose exec postgres psql -U ai_assistant -c "SELECT * FROM pg_extension WHERE extname = 'vector'"

# Test embedding search
curl -X GET "http://localhost:8080/memory/search?query=test&limit=1"
```
