import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'glicko_app.db')

SCHEMA = """
CREATE TABLE IF NOT EXISTS subjects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
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


def init_db():
    conn = get_db()
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
