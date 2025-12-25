"""
SQLite-based conversation storage module.

Provides better performance and querying capabilities compared to JSONL.
"""

import sqlite3
import json
import asyncio
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime
from contextlib import asynccontextmanager
import threading

from log_config import logger


class SQLiteStorage:
    """SQLite-based conversation storage with thread-safe operations."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local connection."""
        if not hasattr(self._local, 'conn'):
            self._local.conn = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
                timeout=30.0
            )
            self._local.conn.row_factory = sqlite3.Row
            # Enable WAL mode for better concurrency
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA foreign_keys=ON")
        return self._local.conn

    def _init_db(self):
        """Initialize database schema."""
        conn = self._get_connection()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL DEFAULT 'New Conversation',
                created_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
                updated_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_conversation_id
            ON messages(conversation_id)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_conversations_updated_at
            ON conversations(updated_at DESC)
        """)
        conn.commit()
        logger.info(f"SQLite database initialized at {self.db_path}")

    async def load(self):
        """Load is no-op for SQLite (data is loaded on query)."""
        logger.info("SQLite storage ready")

    async def save(self):
        """Save is no-op for SQLite (auto-commit on write)."""
        pass

    def get_all(self) -> List[Dict]:
        """Get all conversations sorted by updated_at."""
        conn = self._get_connection()
        cursor = conn.execute("""
            SELECT id, title, created_at, updated_at
            FROM conversations
            ORDER BY updated_at DESC
        """)
        conversations = []
        for row in cursor.fetchall():
            # Get message count
            msg_count = conn.execute(
                "SELECT COUNT(*) FROM messages WHERE conversation_id = ?",
                (row['id'],)
            ).fetchone()[0]
            conversations.append({
                'id': row['id'],
                'title': row['title'],
                'created_at': row['created_at'],
                'updated_at': row['updated_at'],
                'messages': []  # Loaded on demand via get()
            })
        return conversations

    def get(self, conv_id: str) -> Optional[Dict]:
        """Get a conversation by ID with all messages."""
        conn = self._get_connection()
        # Get conversation metadata
        conv_row = conn.execute(
            "SELECT id, title, created_at, updated_at FROM conversations WHERE id = ?",
            (conv_id,)
        ).fetchone()
        if not conv_row:
            return None
        # Get messages
        msg_rows = conn.execute(
            "SELECT id, role, content, timestamp FROM messages WHERE conversation_id = ? ORDER BY timestamp ASC",
            (conv_id,)
        ).fetchall()
        messages = []
        for row in msg_rows:
            content = json.loads(row['content'])
            messages.append({
                'id': row['id'],
                'role': row['role'],
                'content': content,
                'timestamp': row['timestamp']
            })
        return {
            'id': conv_row['id'],
            'title': conv_row['title'],
            'created_at': conv_row['created_at'],
            'updated_at': conv_row['updated_at'],
            'messages': messages
        }

    def set(self, conv: Dict) -> None:
        """Set/update a conversation."""
        conn = self._get_connection()
        conv_id = conv['id']
        title = conv.get('title', 'New Conversation')
        created_at = conv.get('created_at', int(datetime.now().timestamp()))
        updated_at = conv.get('updated_at', int(datetime.now().timestamp()))
        # Upsert conversation
        conn.execute("""
            INSERT INTO conversations (id, title, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                title = excluded.title,
                updated_at = excluded.updated_at
        """, (conv_id, title, created_at, updated_at))
        # Delete existing messages and re-insert
        conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conv_id,))
        for msg in conv.get('messages', []):
            conn.execute("""
                INSERT INTO messages (id, conversation_id, role, content, timestamp)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    role = excluded.role,
                    content = excluded.content,
                    timestamp = excluded.timestamp
            """, (
                msg['id'],
                conv_id,
                msg['role'],
                json.dumps(msg['content'], ensure_ascii=False),
                msg.get('timestamp', updated_at)
            ))
        conn.commit()
        logger.debug(f"Saved conversation {conv_id} to SQLite")

    def delete(self, conv_id: str) -> bool:
        """Delete a conversation."""
        conn = self._get_connection()
        cursor = conn.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
        conn.commit()
        deleted = cursor.rowcount > 0
        if deleted:
            logger.info(f"Deleted conversation {conv_id}")
        return deleted

    def update_timestamp(self, conv_id: str) -> None:
        """Update the updated_at timestamp for a conversation."""
        conn = self._get_connection()
        conn.execute(
            "UPDATE conversations SET updated_at = strftime('%s', 'now') WHERE id = ?",
            (conv_id,)
        )
        conn.commit()

    async def migrate_from_jsonl(self, jsonl_path: Path) -> int:
        """Migrate conversations from JSONL file to SQLite."""
        if not jsonl_path.exists():
            logger.info(f"No JSONL file found at {jsonl_path}, skipping migration")
            return 0
        count = 0
        try:
            with open(jsonl_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        conv = json.loads(line)
                        self.set(conv)
                        count += 1
            logger.info(f"Migrated {count} conversations from JSONL to SQLite")
            # Backup old JSONL file
            backup_path = jsonl_path.with_suffix('.jsonl.bak')
            jsonl_path.rename(backup_path)
            logger.info(f"Backed up old JSONL to {backup_path}")
        except Exception as e:
            logger.error(f"Failed to migrate from JSONL: {e}")
        return count


# --- Global instances ---
CONVERSATIONS_DIR = Path("conversations")
CONVERSATIONS_DIR.mkdir(exist_ok=True)

conversation_storage = SQLiteStorage(CONVERSATIONS_DIR / "conversations.db")

__all__ = ["SQLiteStorage", "conversation_storage", "CONVERSATIONS_DIR"]
