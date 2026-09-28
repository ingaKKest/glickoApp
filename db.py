import sqlite3
import os
import secrets
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'glicko_app.db')

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS subjects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    UNIQUE(user_id, name)
);

CREATE TABLE IF NOT EXISTS topics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    rating REAL NOT NULL DEFAULT 1500,
    rd REAL NOT NULL DEFAULT 350,
    last_update TEXT,
    pending_results TEXT NOT NULL DEFAULT '[]',
    UNIQUE(subject_id, name)
);

CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id INTEGER NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    answer TEXT,
    image_filename TEXT,
    answer_image_filename TEXT,
    rating REAL NOT NULL DEFAULT 1500,
    rd REAL NOT NULL DEFAULT 350,
    last_update TEXT,
    sm2_n INTEGER NOT NULL DEFAULT 0,
    sm2_ef REAL NOT NULL DEFAULT 2.5,
    sm2_interval REAL NOT NULL DEFAULT 0,
    next_eligible TEXT
);

CREATE TABLE IF NOT EXISTS answer_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    topic_id INTEGER NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    score REAL NOT NULL,
    answered_at TEXT NOT NULL
);
"""


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _column_exists(conn, table, column):
    cols = [r['name'] for r in conn.execute(f"PRAGMA table_info({table})")]
    return column in cols


def init_db():
    """Create tables for a fresh install, and migrate an older database
    (from before accounts/images existed) in place."""
    conn = get_db()
    conn.executescript(SCHEMA)
    conn.commit()

    # --- migration: pre-accounts database (subjects had no user_id) ---
    if not _column_exists(conn, 'subjects', 'user_id'):
        conn.execute("ALTER TABLE subjects ADD COLUMN user_id INTEGER")
        orphan_count = conn.execute(
            "SELECT COUNT(*) c FROM subjects WHERE user_id IS NULL"
        ).fetchone()['c']
        if orphan_count:
            from werkzeug.security import generate_password_hash
            temp_password = secrets.token_urlsafe(8)
            cur = conn.execute(
                "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
                ('migrated', generate_password_hash(temp_password), datetime.utcnow().isoformat())
            )
            migrated_user_id = cur.lastrowid
            conn.execute("UPDATE subjects SET user_id = ? WHERE user_id IS NULL", (migrated_user_id,))
            print("\n[glicko-study] Found existing data from before accounts existed.")
            print(f"[glicko-study] Created an account for it -> username: migrated   password: {temp_password}")
            print("[glicko-study] Log in with that to see your old subjects, then change your password.\n")

    # --- migration: pre-image database ---
    if not _column_exists(conn, 'questions', 'image_filename'):
        conn.execute("ALTER TABLE questions ADD COLUMN image_filename TEXT")
    if not _column_exists(conn, 'questions', 'answer_image_filename'):
        conn.execute("ALTER TABLE questions ADD COLUMN answer_image_filename TEXT")

    conn.commit()
    conn.close()
