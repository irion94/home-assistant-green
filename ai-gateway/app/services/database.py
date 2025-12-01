"""Database service for AI assistant memory, knowledge, and preferences."""

from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import asyncpg
from asyncpg import Pool

logger = logging.getLogger(__name__)


class DatabaseService:
    """Service for managing AI assistant database operations."""

    def __init__(self) -> None:
        """Initialize database service."""
        self.pool: Pool | None = None
        self._config = {
            "host": os.getenv("POSTGRES_HOST", "localhost"),
            "port": int(os.getenv("POSTGRES_PORT", "5432")),
            "user": os.getenv("POSTGRES_USER", "ai_assistant"),
            "password": os.getenv("POSTGRES_PASSWORD", "changeme"),
            "database": os.getenv("POSTGRES_DB", "ai_assistant"),
        }
        self._cache_ttl = int(os.getenv("CACHE_TTL_SECONDS", "3600"))

    async def connect(self) -> None:
        """Create database connection pool.

        Phase 7: Optimized connection pooling for better performance.
        - min_size: 5 connections (up from 2)
        - max_size: 20 connections (up from 10)
        - max_queries: 50000 (recycle connections after 50k queries)
        - max_inactive_connection_lifetime: 300s (5 minutes)
        """
        if self.pool is not None:
            return

        try:
            self.pool = await asyncpg.create_pool(
                host=self._config["host"],
                port=self._config["port"],
                user=self._config["user"],
                password=self._config["password"],
                database=self._config["database"],
                min_size=5,          # Phase 7: Increased from 2
                max_size=20,         # Phase 7: Increased from 10
                max_queries=50000,   # Phase 7: Recycle connections after N queries
                max_inactive_connection_lifetime=300,  # Phase 7: 5 minutes
            )
            logger.info("Database connection pool created (Phase 7: optimized)")
            await self._run_migrations()
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    async def disconnect(self) -> None:
        """Close database connection pool."""
        if self.pool:
            await self.pool.close()
            self.pool = None
            logger.info("Database connection pool closed")

    async def _run_migrations(self) -> None:
        """Run database migrations."""
        if not self.pool:
            return

        migrations_dir = Path(__file__).parent.parent.parent / "migrations"
        if not migrations_dir.exists():
            logger.warning(f"Migrations directory not found: {migrations_dir}")
            return

        async with self.pool.acquire() as conn:
            # Create migrations tracking table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    id SERIAL PRIMARY KEY,
                    filename VARCHAR(255) UNIQUE NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Get applied migrations
            applied = await conn.fetch("SELECT filename FROM schema_migrations")
            applied_files = {row["filename"] for row in applied}

            # Run pending migrations
            for migration_file in sorted(migrations_dir.glob("*.sql")):
                if migration_file.name not in applied_files:
                    logger.info(f"Running migration: {migration_file.name}")
                    sql = migration_file.read_text()
                    await conn.execute(sql)
                    await conn.execute(
                        "INSERT INTO schema_migrations (filename) VALUES ($1)",
                        migration_file.name,
                    )
                    logger.info(f"Migration completed: {migration_file.name}")

    # ==========================================
    # Conversation Operations
    # ==========================================

    async def save_conversation(
        self,
        session_id: str,
        role: str,
        content: str,
        language: str | None = None,
        intent: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """Save a conversation message."""
        if not self.pool:
            raise RuntimeError("Database not connected")

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO conversations (session_id, role, content, language, intent, metadata)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id
                """,
                session_id,
                role,
                content,
                language,
                intent,
                json.dumps(metadata or {}),
            )
            return int(row["id"])

    async def get_conversation_history(
        self,
        session_id: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Get conversation history for a session."""
        if not self.pool:
            raise RuntimeError("Database not connected")

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, role, content, language, intent, created_at, metadata
                FROM conversations
                WHERE session_id = $1
                ORDER BY created_at DESC
                LIMIT $2
                """,
                session_id,
                limit,
            )
            return [
                {
                    "id": row["id"],
                    "role": row["role"],
                    "content": row["content"],
                    "language": row["language"],
                    "intent": row["intent"],
                    "created_at": row["created_at"].isoformat(),
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                }
                for row in reversed(rows)
            ]

    async def get_recent_sessions(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get recent conversation sessions."""
        if not self.pool:
            raise RuntimeError("Database not connected")

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT session_id,
                       COUNT(*) as message_count,
                       MIN(created_at) as started_at,
                       MAX(created_at) as last_message_at
                FROM conversations
                GROUP BY session_id
                ORDER BY last_message_at DESC
                LIMIT $1
                """,
                limit,
            )
            return [
                {
                    "session_id": row["session_id"],
                    "message_count": row["message_count"],
                    "started_at": row["started_at"].isoformat(),
                    "last_message_at": row["last_message_at"].isoformat(),
                }
                for row in rows
            ]

    # ==========================================
    # Knowledge/RAG Operations
    # ==========================================

    async def add_knowledge(
        self,
        content: str,
        embedding: list[float],
        source: str | None = None,
        tags: list[str] | None = None,
    ) -> int:
        """Add a knowledge entry with embedding."""
        if not self.pool:
            raise RuntimeError("Database not connected")

        async with self.pool.acquire() as conn:
            # Convert embedding list to pgvector format
            embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
            row = await conn.fetchrow(
                """
                INSERT INTO knowledge (content, embedding, source, tags)
                VALUES ($1, $2::vector, $3, $4)
                RETURNING id
                """,
                content,
                embedding_str,
                source,
                tags or [],
            )
            return int(row["id"])

    async def search_knowledge(
        self,
        query_embedding: list[float],
        limit: int = 5,
        min_similarity: float = 0.5,
    ) -> list[dict[str, Any]]:
        """Search knowledge base using vector similarity."""
        if not self.pool:
            raise RuntimeError("Database not connected")

        async with self.pool.acquire() as conn:
            embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"
            rows = await conn.fetch(
                """
                SELECT id, content, source, tags, created_at,
                       1 - (embedding <=> $1::vector) as similarity
                FROM knowledge
                WHERE embedding IS NOT NULL
                ORDER BY embedding <=> $1::vector
                LIMIT $2
                """,
                embedding_str,
                limit,
            )
            return [
                {
                    "id": row["id"],
                    "content": row["content"],
                    "source": row["source"],
                    "tags": row["tags"],
                    "similarity": float(row["similarity"]),
                    "created_at": row["created_at"].isoformat(),
                }
                for row in rows
                if row["similarity"] >= min_similarity
            ]

    async def get_knowledge_by_tags(
        self,
        tags: list[str],
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Get knowledge entries by tags."""
        if not self.pool:
            raise RuntimeError("Database not connected")

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, content, source, tags, created_at
                FROM knowledge
                WHERE tags && $1
                ORDER BY created_at DESC
                LIMIT $2
                """,
                tags,
                limit,
            )
            return [
                {
                    "id": row["id"],
                    "content": row["content"],
                    "source": row["source"],
                    "tags": row["tags"],
                    "created_at": row["created_at"].isoformat(),
                }
                for row in rows
            ]

    async def delete_knowledge(self, knowledge_id: int) -> bool:
        """Delete a knowledge entry."""
        if not self.pool:
            raise RuntimeError("Database not connected")

        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM knowledge WHERE id = $1",
                knowledge_id,
            )
            return result == "DELETE 1"

    # ==========================================
    # Preferences Operations
    # ==========================================

    async def set_preference(
        self,
        key: str,
        value: Any,
        category: str | None = None,
    ) -> None:
        """Set a user preference."""
        if not self.pool:
            raise RuntimeError("Database not connected")

        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO preferences (key, value, category)
                VALUES ($1, $2, $3)
                ON CONFLICT (key) DO UPDATE
                SET value = $2, category = COALESCE($3, preferences.category)
                """,
                key,
                json.dumps(value),
                category,
            )

    async def get_preference(self, key: str, default: Any = None) -> Any:
        """Get a user preference."""
        if not self.pool:
            raise RuntimeError("Database not connected")

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT value FROM preferences WHERE key = $1",
                key,
            )
            if row:
                return json.loads(row["value"])
            return default

    async def get_preferences_by_category(
        self,
        category: str,
    ) -> dict[str, Any]:
        """Get all preferences in a category."""
        if not self.pool:
            raise RuntimeError("Database not connected")

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT key, value FROM preferences WHERE category = $1",
                category,
            )
            return {row["key"]: json.loads(row["value"]) for row in rows}

    async def delete_preference(self, key: str) -> bool:
        """Delete a preference."""
        if not self.pool:
            raise RuntimeError("Database not connected")

        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM preferences WHERE key = $1",
                key,
            )
            return result == "DELETE 1"

    # ==========================================
    # Cache Operations
    # ==========================================

    @staticmethod
    def _hash_query(query: str) -> str:
        """Generate hash for query caching."""
        return hashlib.sha256(query.lower().strip().encode()).hexdigest()

    async def get_cached_response(self, query: str) -> str | None:
        """Get cached response for a query."""
        if not self.pool:
            raise RuntimeError("Database not connected")

        query_hash = self._hash_query(query)

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT response FROM response_cache
                WHERE query_hash = $1
                AND (expires_at IS NULL OR expires_at > NOW())
                """,
                query_hash,
            )
            if row:
                # Update hit count
                await conn.execute(
                    """
                    UPDATE response_cache
                    SET hit_count = hit_count + 1
                    WHERE query_hash = $1
                    """,
                    query_hash,
                )
                return str(row["response"])
            return None

    async def cache_response(
        self,
        query: str,
        response: str,
        ttl_seconds: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Cache a response."""
        if not self.pool:
            raise RuntimeError("Database not connected")

        query_hash = self._hash_query(query)
        ttl = ttl_seconds or self._cache_ttl
        expires_at = datetime.utcnow() + timedelta(seconds=ttl)

        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO response_cache (query_hash, query_text, response, expires_at, metadata)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (query_hash) DO UPDATE
                SET response = $3, expires_at = $4, hit_count = 0
                """,
                query_hash,
                query,
                response,
                expires_at,
                json.dumps(metadata or {}),
            )

    async def clear_expired_cache(self) -> int:
        """Clear expired cache entries."""
        if not self.pool:
            raise RuntimeError("Database not connected")

        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM response_cache WHERE expires_at < NOW()"
            )
            # Parse "DELETE X" to get count
            count = int(result.split()[1]) if result else 0
            logger.info(f"Cleared {count} expired cache entries")
            return count

    async def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        if not self.pool:
            raise RuntimeError("Database not connected")

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT
                    COUNT(*) as total_entries,
                    SUM(hit_count) as total_hits,
                    COUNT(*) FILTER (WHERE expires_at > NOW()) as active_entries
                FROM response_cache
                """
            )
            return {
                "total_entries": row["total_entries"],
                "total_hits": row["total_hits"] or 0,
                "active_entries": row["active_entries"],
            }

    # ==========================================
    # Training Data Operations
    # ==========================================

    async def save_training_data(
        self,
        input_text: str,
        output_text: str,
        feedback_score: int | None = None,
        interaction_type: str | None = None,
        language: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """Save training data entry."""
        if not self.pool:
            raise RuntimeError("Database not connected")

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO training_data
                (input_text, output_text, feedback_score, interaction_type, language, metadata)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id
                """,
                input_text,
                output_text,
                feedback_score,
                interaction_type,
                language,
                json.dumps(metadata or {}),
            )
            return int(row["id"])

    async def update_feedback(
        self,
        training_id: int,
        score: int,
    ) -> bool:
        """Update feedback score for training data."""
        if not self.pool:
            raise RuntimeError("Database not connected")

        async with self.pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE training_data
                SET feedback_score = $2
                WHERE id = $1
                """,
                training_id,
                score,
            )
            return result == "UPDATE 1"

    async def export_training_data(
        self,
        min_score: int = 3,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        """Export high-quality training data as JSONL format."""
        if not self.pool:
            raise RuntimeError("Database not connected")

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, input_text, output_text, language, interaction_type
                FROM training_data
                WHERE (feedback_score IS NULL OR feedback_score >= $1)
                AND exported = FALSE
                ORDER BY created_at
                LIMIT $2
                """,
                min_score,
                limit,
            )

            # Mark as exported
            if rows:
                ids = [row["id"] for row in rows]
                await conn.execute(
                    """
                    UPDATE training_data
                    SET exported = TRUE
                    WHERE id = ANY($1)
                    """,
                    ids,
                )

            return [
                {
                    "messages": [
                        {"role": "user", "content": row["input_text"]},
                        {"role": "assistant", "content": row["output_text"]},
                    ],
                    "language": row["language"],
                    "type": row["interaction_type"],
                }
                for row in rows
            ]

    async def get_training_stats(self) -> dict[str, Any]:
        """Get training data statistics."""
        if not self.pool:
            raise RuntimeError("Database not connected")

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE feedback_score >= 4) as high_quality,
                    COUNT(*) FILTER (WHERE exported = TRUE) as exported,
                    AVG(feedback_score) as avg_score
                FROM training_data
                """
            )
            return {
                "total": row["total"],
                "high_quality": row["high_quality"],
                "exported": row["exported"],
                "avg_score": float(row["avg_score"]) if row["avg_score"] else None,
            }


# Singleton instance
db_service = DatabaseService()
