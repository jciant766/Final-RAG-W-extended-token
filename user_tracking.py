"""
User tracking and authentication system for Maltese Law RAG.
Simple implementation for tracking client usage during free trials.
"""

import sqlite3
import hashlib
import secrets
from datetime import datetime
from typing import Optional, Dict, List
import requests
import os
from dotenv import load_dotenv

load_dotenv()


class UserTracker:
    def __init__(self, db_path="user_tracking.db"):
        self.db_path = db_path
        self.telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")  # Your Telegram user ID
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database with users and usage_logs tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT,
                password_hash TEXT NOT NULL,
                api_token TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                total_queries INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                notes TEXT
            )
        ''')

        # Usage logs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usage_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                query TEXT NOT NULL,
                response_length INTEGER,
                sources_count INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ip_address TEXT,
                user_agent TEXT,
                input_tokens INTEGER DEFAULT 0,
                output_tokens INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0,
                cost_usd REAL DEFAULT 0.0,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')

        # Add token/cost columns to existing table if they don't exist (migration)
        try:
            cursor.execute('ALTER TABLE usage_logs ADD COLUMN input_tokens INTEGER DEFAULT 0')
        except:
            pass
        try:
            cursor.execute('ALTER TABLE usage_logs ADD COLUMN output_tokens INTEGER DEFAULT 0')
        except:
            pass
        try:
            cursor.execute('ALTER TABLE usage_logs ADD COLUMN total_tokens INTEGER DEFAULT 0')
        except:
            pass
        try:
            cursor.execute('ALTER TABLE usage_logs ADD COLUMN cost_usd REAL DEFAULT 0.0')
        except:
            pass

        # Sessions table for web auth
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                session_token TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')

        conn.commit()
        conn.close()

    def create_user(self, username: str, password: str, email: str = "", notes: str = "") -> Dict:
        """Create a new user account."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Hash password
        password_hash = hashlib.sha256(password.encode()).hexdigest()

        # Generate unique API token
        api_token = secrets.token_urlsafe(32)

        try:
            cursor.execute('''
                INSERT INTO users (username, email, password_hash, api_token, notes)
                VALUES (?, ?, ?, ?, ?)
            ''', (username, email, password_hash, api_token, notes))

            user_id = cursor.lastrowid
            conn.commit()

            # Send Telegram notification
            self._send_telegram(f"🆕 New user created:\n👤 {username}\n📧 {email}\n📝 {notes}")

            return {
                "success": True,
                "user_id": user_id,
                "username": username,
                "api_token": api_token
            }
        except sqlite3.IntegrityError:
            return {"success": False, "error": "Username already exists"}
        finally:
            conn.close()

    def authenticate(self, username: str, password: str) -> Optional[Dict]:
        """Authenticate user with username/password."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        password_hash = hashlib.sha256(password.encode()).hexdigest()

        cursor.execute('''
            SELECT id, username, email, api_token, is_active
            FROM users
            WHERE username = ? AND password_hash = ?
        ''', (username, password_hash))

        user = cursor.fetchone()

        if user and user[4]:  # Check if user exists and is active
            # Update last login
            cursor.execute('''
                UPDATE users SET last_login = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (user[0],))
            conn.commit()
            conn.close()

            return {
                "id": user[0],
                "username": user[1],
                "email": user[2],
                "api_token": user[3]
            }

        conn.close()
        return None

    def verify_token(self, api_token: str) -> Optional[Dict]:
        """Verify API token and return user info."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, username, email, is_active
            FROM users
            WHERE api_token = ?
        ''', (api_token,))

        user = cursor.fetchone()
        conn.close()

        if user and user[3]:  # Check if active
            return {
                "id": user[0],
                "username": user[1],
                "email": user[2]
            }
        return None

    def log_query(self, user_id: int, query: str, response_length: int = 0,
                  sources_count: int = 0, ip_address: str = "", user_agent: str = "",
                  input_tokens: int = 0, output_tokens: int = 0, cost_usd: float = 0.0):
        """Log a user query for tracking including token usage and cost."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        total_tokens = input_tokens + output_tokens

        # Insert log
        cursor.execute('''
            INSERT INTO usage_logs (user_id, query, response_length, sources_count, ip_address, user_agent,
                                   input_tokens, output_tokens, total_tokens, cost_usd)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, query, response_length, sources_count, ip_address, user_agent,
              input_tokens, output_tokens, total_tokens, cost_usd))

        # Update user's total queries
        cursor.execute('''
            UPDATE users SET total_queries = total_queries + 1
            WHERE id = ?
        ''', (user_id,))

        conn.commit()

        # Get username for notification
        cursor.execute('SELECT username FROM users WHERE id = ?', (user_id,))
        username = cursor.fetchone()[0]

        conn.close()

        # Send Telegram notification
        self._send_telegram(
            f"💬 New query from {username}:\n\n"
            f"❓ {query[:200]}{'...' if len(query) > 200 else ''}\n\n"
            f"📊 Response: {response_length} chars, {sources_count} sources"
        )

    def get_user_stats(self, user_id: int) -> Dict:
        """Get usage statistics for a user."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get user info
        cursor.execute('''
            SELECT username, email, created_at, total_queries, last_login
            FROM users WHERE id = ?
        ''', (user_id,))
        user = cursor.fetchone()

        # Get recent queries
        cursor.execute('''
            SELECT query, timestamp, response_length, sources_count
            FROM usage_logs
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT 10
        ''', (user_id,))
        recent_queries = cursor.fetchall()

        conn.close()

        return {
            "username": user[0],
            "email": user[1],
            "created_at": user[2],
            "total_queries": user[3],
            "last_login": user[4],
            "recent_queries": [
                {
                    "query": q[0],
                    "timestamp": q[1],
                    "response_length": q[2],
                    "sources_count": q[3]
                }
                for q in recent_queries
            ]
        }

    def get_all_users(self) -> List[Dict]:
        """Get all users with their stats."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, username, email, created_at, total_queries, last_login, is_active, notes
            FROM users
            ORDER BY created_at DESC
        ''')
        users = cursor.fetchall()
        conn.close()

        return [
            {
                "id": u[0],
                "username": u[1],
                "email": u[2],
                "created_at": u[3],
                "total_queries": u[4],
                "last_login": u[5],
                "is_active": bool(u[6]),
                "notes": u[7]
            }
            for u in users
        ]

    def deactivate_user(self, user_id: int):
        """Deactivate a user account."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET is_active = 0 WHERE id = ?', (user_id,))
        conn.commit()
        conn.close()

    def _send_telegram(self, message: str):
        """Send notification to Telegram."""
        if not self.telegram_bot_token or not self.telegram_chat_id:
            return  # Skip if not configured

        try:
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            data = {
                "chat_id": self.telegram_chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
            requests.post(url, json=data, timeout=5)
        except Exception as e:
            print(f"Failed to send Telegram notification: {e}")


# Singleton instance
tracker = UserTracker()
