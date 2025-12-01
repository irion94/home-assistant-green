-- Phase 7: Performance Optimization - Database Indexes
-- Purpose: Add indexes to improve query performance from 200ms to <50ms
-- Created: 2025-12-01

-- ==============================================
-- Conversations Table Indexes
-- ==============================================

-- Session ID lookup (most common query pattern)
CREATE INDEX IF NOT EXISTS idx_conversations_session_id
ON conversations(session_id);

-- Timestamp-based sorting for recent conversations
CREATE INDEX IF NOT EXISTS idx_conversations_created_at
ON conversations(created_at DESC);

-- Room-based filtering
CREATE INDEX IF NOT EXISTS idx_conversations_room_id
ON conversations(room_id);

-- Composite index for the most common query:
-- "Get recent conversations for a session in a specific room"
-- This covers: WHERE session_id = X AND room_id = Y ORDER BY created_at DESC
CREATE INDEX IF NOT EXISTS idx_conversations_session_room_created
ON conversations(session_id, room_id, created_at DESC);

-- ==============================================
-- Training Data Table Indexes
-- ==============================================

-- Intent lookup for pattern matching
CREATE INDEX IF NOT EXISTS idx_training_data_intent
ON training_data(intent);

-- Recent patterns lookup
CREATE INDEX IF NOT EXISTS idx_training_data_created_at
ON training_data(created_at DESC);

-- Language-based filtering
CREATE INDEX IF NOT EXISTS idx_training_data_language
ON training_data(language)
WHERE language IS NOT NULL;

-- Composite index for learning queries:
-- "Get recent patterns for a specific intent"
CREATE INDEX IF NOT EXISTS idx_training_data_intent_created
ON training_data(intent, created_at DESC);

-- ==============================================
-- Preferences Table Indexes
-- ==============================================

-- Key lookup (primary access pattern)
CREATE INDEX IF NOT EXISTS idx_preferences_key
ON preferences(key);

-- Category-based filtering
CREATE INDEX IF NOT EXISTS idx_preferences_category
ON preferences(category);

-- Composite index for categorized preferences
CREATE INDEX IF NOT EXISTS idx_preferences_category_key
ON preferences(category, key);

-- ==============================================
-- Performance Maintenance
-- ==============================================

-- Reclaim storage and update statistics for query planner
VACUUM ANALYZE conversations;
VACUUM ANALYZE training_data;
VACUUM ANALYZE preferences;

-- ==============================================
-- Verification Queries
-- ==============================================

-- Show all indexes on each table
-- Uncomment to verify indexes after migration:

-- \di+ idx_conversations_*
-- \di+ idx_training_data_*
-- \di+ idx_preferences_*

-- Query to check index usage statistics:
-- SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
-- FROM pg_stat_user_indexes
-- WHERE schemaname = 'public'
-- ORDER BY idx_scan DESC;
