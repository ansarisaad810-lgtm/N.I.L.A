import sqlite3
import json
import os
from typing import List, Dict, Any

class LocalMemory:
    def __init__(self, db_path: str = "brain/core/nila_memory.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Chat context memory
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversation_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            # File location memory cache
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS file_cache (
                    filename TEXT PRIMARY KEY,
                    full_path TEXT NOT NULL,
                    last_accessed DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            # Alarms & Reminders table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message TEXT NOT NULL,
                    trigger_time TEXT NOT NULL,
                    status TEXT DEFAULT 'PENDING'
                )
            ''')
            conn.commit()

    def add_message(self, role: str, content: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.cursor().execute(
                "INSERT INTO conversation_history (role, content) VALUES (?, ?)",
                (role, content)
            )
            conn.commit()

    def get_recent_history(self, limit: int = 10) -> List[Dict[str, str]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT role, content FROM conversation_history ORDER BY id DESC LIMIT ?",
                (limit,)
            )
            rows = cursor.fetchall()
            # Return in chronological order
            return [{"role": r[0], "content": r[1]} for r in reversed(rows)]

    def remember_file(self, filename: str, full_path: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.cursor().execute(
                "INSERT OR REPLACE INTO file_cache (filename, full_path) VALUES (?, ?)",
                (filename.lower(), full_path)
            )
            conn.commit()

    def lookup_file(self, filename: str) -> str:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT full_path FROM file_cache WHERE filename LIKE ?",
                (f"%{filename.lower()}%",)
            )
            row = cursor.fetchone()
            return row[0] if row else None

    def add_reminder(self, message: str, trigger_time: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.cursor().execute(
                "INSERT INTO reminders (message, trigger_time) VALUES (?, ?)",
                (message, trigger_time)
            )
            conn.commit()

memory = LocalMemory()
