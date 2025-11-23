-- AI Assistant Database Schema
-- Migration: 001_initial_schema
-- Created: 2024-11-23

-- Enable pgvector extension for embedding storage
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================
-- 1. Conversations Table
-- Store chat history for memory across sessions
-- ============================================
CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL,  -- 'user' or 'assistant'
    content TEXT NOT NULL,
    language VARCHAR(10),
    intent VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_conversations_session ON conversations(session_id);
CREATE INDEX IF NOT EXISTS idx_conversations_created ON conversations(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversations_language ON conversations(language);

-- ============================================
-- 2. Knowledge Table (RAG)
-- Store documents/facts for retrieval-augmented generation
-- ============================================
CREATE TABLE IF NOT EXISTS knowledge (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    embedding vector(384),  -- nomic-embed-text dimension
    source VARCHAR(255),
    tags TEXT[] DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- IVFFlat index for fast similarity search (tune lists based on data size)
CREATE INDEX IF NOT EXISTS idx_knowledge_embedding ON knowledge
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS idx_knowledge_tags ON knowledge USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_knowledge_source ON knowledge(source);

-- ============================================
-- 3. User Preferences Table
-- Store settings, learned behaviors, personalization
-- ============================================
CREATE TABLE IF NOT EXISTS preferences (
    id SERIAL PRIMARY KEY,
    key VARCHAR(255) UNIQUE NOT NULL,
    value JSONB NOT NULL,
    category VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_preferences_category ON preferences(category);
CREATE INDEX IF NOT EXISTS idx_preferences_key ON preferences(key);

-- ============================================
-- 4. Response Cache Table
-- Cache common queries for faster responses
-- ============================================
CREATE TABLE IF NOT EXISTS response_cache (
    id SERIAL PRIMARY KEY,
    query_hash VARCHAR(64) UNIQUE NOT NULL,
    query_text TEXT NOT NULL,
    response TEXT NOT NULL,
    hit_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_cache_hash ON response_cache(query_hash);
CREATE INDEX IF NOT EXISTS idx_cache_expires ON response_cache(expires_at);

-- ============================================
-- 5. Training Data Table
-- Store successful interactions for fine-tuning
-- ============================================
CREATE TABLE IF NOT EXISTS training_data (
    id SERIAL PRIMARY KEY,
    input_text TEXT NOT NULL,
    output_text TEXT NOT NULL,
    feedback_score INTEGER CHECK (feedback_score >= 1 AND feedback_score <= 5),
    interaction_type VARCHAR(50),  -- 'command', 'question', 'conversation'
    language VARCHAR(10),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    exported BOOLEAN DEFAULT FALSE,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_training_feedback ON training_data(feedback_score);
CREATE INDEX IF NOT EXISTS idx_training_exported ON training_data(exported);
CREATE INDEX IF NOT EXISTS idx_training_type ON training_data(interaction_type);

-- ============================================
-- Helper Functions
-- ============================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for auto-updating updated_at
CREATE TRIGGER update_knowledge_updated_at
    BEFORE UPDATE ON knowledge
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_preferences_updated_at
    BEFORE UPDATE ON preferences
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- Initial Data (Optional)
-- ============================================

-- Default preferences
INSERT INTO preferences (key, value, category)
VALUES
    ('system.language', '"pl"', 'system'),
    ('system.tts_speed', '1.2', 'system'),
    ('system.wake_word', '"hey_jarvis"', 'system')
ON CONFLICT (key) DO NOTHING;
