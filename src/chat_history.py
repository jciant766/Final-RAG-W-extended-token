"""
Chat history management for Maltese Law RAG.
Stores conversations in SQLite for persistence and retrieval.
"""

import sqlite3
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class ChatHistoryManager:
    """Manages chat conversation history with SQLite backend."""

    def __init__(self, db_path: str = "chat_history.db"):
        """
        Initialize chat history manager.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self._init_database()

    def _init_database(self):
        """Create database tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chats (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    message_count INTEGER DEFAULT 0,
                    metadata TEXT
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    chat_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    metadata TEXT,
                    FOREIGN KEY (chat_id) REFERENCES chats(id) ON DELETE CASCADE
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_chat_id
                ON messages(chat_id)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp
                ON chats(updated_at DESC)
            """)

            conn.commit()
            logger.info(f"Chat history database initialized at {self.db_path}")

    def save_chat(
        self,
        messages: List[Dict],
        chat_id: Optional[str] = None,
        title: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Save or update a chat conversation.

        Args:
            messages: List of message dicts with 'role' and 'content'
            chat_id: Existing chat ID to update, or None for new chat
            title: Chat title (auto-generated from first message if None)
            metadata: Additional metadata to store

        Returns:
            Chat ID (generated or provided)
        """
        if not messages:
            raise ValueError("Cannot save empty chat")

        # Generate chat ID if new
        if not chat_id:
            chat_id = str(uuid.uuid4())

        # Generate title from first user message if not provided
        if not title:
            first_user_msg = next((m for m in messages if m.get('role') == 'user'), None)
            if first_user_msg:
                content = first_user_msg.get('content', '')
                title = content[:60] + ('...' if len(content) > 60 else '')
            else:
                title = f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        now = datetime.now().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            # Check if chat exists
            cursor = conn.execute("SELECT id FROM chats WHERE id = ?", (chat_id,))
            exists = cursor.fetchone() is not None

            if exists:
                # Update existing chat
                conn.execute("""
                    UPDATE chats
                    SET title = ?, updated_at = ?, message_count = ?, metadata = ?
                    WHERE id = ?
                """, (title, now, len(messages), json.dumps(metadata or {}), chat_id))

                # Delete old messages
                conn.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
            else:
                # Insert new chat
                conn.execute("""
                    INSERT INTO chats (id, title, created_at, updated_at, message_count, metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (chat_id, title, now, now, len(messages), json.dumps(metadata or {})))

            # Insert all messages
            for msg in messages:
                msg_id = str(uuid.uuid4())
                msg_metadata = {
                    k: v for k, v in msg.items()
                    if k not in ('role', 'content')
                }

                conn.execute("""
                    INSERT INTO messages (id, chat_id, role, content, timestamp, metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    msg_id,
                    chat_id,
                    msg.get('role', 'user'),
                    msg.get('content', ''),
                    msg.get('timestamp', now),
                    json.dumps(msg_metadata)
                ))

            conn.commit()

        logger.info(f"{'Updated' if exists else 'Saved'} chat {chat_id} with {len(messages)} messages")
        return chat_id

    def load_chat(self, chat_id: str) -> Optional[Dict]:
        """
        Load a chat conversation by ID.

        Args:
            chat_id: Chat ID to load

        Returns:
            Dict with chat info and messages, or None if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Get chat info
            cursor = conn.execute("""
                SELECT * FROM chats WHERE id = ?
            """, (chat_id,))

            chat_row = cursor.fetchone()
            if not chat_row:
                return None

            # Get messages
            cursor = conn.execute("""
                SELECT role, content, timestamp, metadata
                FROM messages
                WHERE chat_id = ?
                ORDER BY timestamp ASC
            """, (chat_id,))

            messages = []
            for row in cursor.fetchall():
                msg = {
                    'role': row['role'],
                    'content': row['content'],
                    'timestamp': row['timestamp']
                }

                # Add metadata if present
                if row['metadata']:
                    try:
                        msg.update(json.loads(row['metadata']))
                    except json.JSONDecodeError:
                        pass

                messages.append(msg)

            return {
                'id': chat_row['id'],
                'title': chat_row['title'],
                'created_at': chat_row['created_at'],
                'updated_at': chat_row['updated_at'],
                'message_count': chat_row['message_count'],
                'metadata': json.loads(chat_row['metadata'] or '{}'),
                'messages': messages
            }

    def list_chats(self, limit: int = 50, offset: int = 0) -> List[Dict]:
        """
        List all saved chats (most recent first).

        Args:
            limit: Maximum number of chats to return
            offset: Number of chats to skip

        Returns:
            List of chat summaries
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            cursor = conn.execute("""
                SELECT id, title, created_at, updated_at, message_count, metadata
                FROM chats
                ORDER BY updated_at DESC
                LIMIT ? OFFSET ?
            """, (limit, offset))

            chats = []
            for row in cursor.fetchall():
                chats.append({
                    'id': row['id'],
                    'title': row['title'],
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at'],
                    'message_count': row['message_count'],
                    'metadata': json.loads(row['metadata'] or '{}')
                })

            return chats

    def delete_chat(self, chat_id: str) -> bool:
        """
        Delete a chat and all its messages.

        Args:
            chat_id: Chat ID to delete

        Returns:
            True if deleted, False if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM chats WHERE id = ?", (chat_id,))
            conn.commit()

            deleted = cursor.rowcount > 0
            if deleted:
                logger.info(f"Deleted chat {chat_id}")

            return deleted

    def search_chats(self, query: str, limit: int = 20) -> List[Dict]:
        """
        Search chats by title or content.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of matching chat summaries
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            cursor = conn.execute("""
                SELECT DISTINCT c.id, c.title, c.created_at, c.updated_at,
                       c.message_count, c.metadata
                FROM chats c
                LEFT JOIN messages m ON c.id = m.chat_id
                WHERE c.title LIKE ? OR m.content LIKE ?
                ORDER BY c.updated_at DESC
                LIMIT ?
            """, (f"%{query}%", f"%{query}%", limit))

            return [dict(row) for row in cursor.fetchall()]

    def get_stats(self) -> Dict:
        """Get database statistics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM chats")
            total_chats = cursor.fetchone()[0]

            cursor = conn.execute("SELECT COUNT(*) FROM messages")
            total_messages = cursor.fetchone()[0]

            return {
                'total_chats': total_chats,
                'total_messages': total_messages,
                'database_size': self.db_path.stat().st_size if self.db_path.exists() else 0
            }
