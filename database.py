import sqlite3
import hashlib
import os
from datetime import datetime


DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "learning_platform.db")

SKILL_LEVELS = {
    1: "Beginner",
    2: "Moderate",
    3: "Intermediate",
    4: "Expert",
}

TOPICS = [
    "C Programming",
    "Python",
    "Java",
    "JavaScript",
    "SQL",
    "Data Structures",
    "Algorithms",
    "HTML/CSS",
]


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def hash_password(password, salt=None):
    if salt is None:
        salt = os.urandom(16).hex()
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000).hex()
    return salt, hashed


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            full_name TEXT NOT NULL,
            email TEXT DEFAULT '',
            nt_id TEXT DEFAULT '',
            department TEXT DEFAULT '',
            team TEXT DEFAULT '',
            years_of_experience INTEGER DEFAULT 0,
            is_admin INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS user_skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            topic TEXT NOT NULL,
            self_rated_level INTEGER DEFAULT 1,
            validated_level INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(user_id, topic)
        );

        CREATE TABLE IF NOT EXISTS quiz_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            topic TEXT NOT NULL,
            level INTEGER NOT NULL,
            score INTEGER NOT NULL,
            total_questions INTEGER NOT NULL,
            passed INTEGER NOT NULL,
            attempted_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)

    # Seed admin users if they don't exist
    admins = [
        ("naveen", "Naveen", "admin123"),
        ("kailash", "Kailash", "admin123"),
    ]
    for username, full_name, password in admins:
        cur.execute("SELECT id FROM users WHERE username = ?", (username,))
        if cur.fetchone() is None:
            salt, pw_hash = hash_password(password)
            cur.execute(
                "INSERT INTO users (username, password_hash, salt, full_name, is_admin) VALUES (?, ?, ?, ?, 1)",
                (username, pw_hash, salt, full_name),
            )

    conn.commit()
    conn.close()


# ── User operations ──────────────────────────────────────────────

def authenticate(username, password):
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    if row is None:
        return None
    _, pw_hash = hash_password(password, row["salt"])
    if pw_hash == row["password_hash"]:
        return dict(row)
    return None


def register_user(username, password, full_name, email=""):
    conn = get_connection()
    salt, pw_hash = hash_password(password)
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash, salt, full_name, email) VALUES (?, ?, ?, ?, ?)",
            (username, pw_hash, salt, full_name, email),
        )
        conn.commit()
        return True, "Registration successful."
    except sqlite3.IntegrityError:
        return False, "Username already exists."
    finally:
        conn.close()


def get_all_users():
    conn = get_connection()
    rows = conn.execute("SELECT id, username, full_name, email, is_admin, created_at FROM users").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_user(user_id):
    conn = get_connection()
    conn.execute("DELETE FROM user_skills WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM quiz_attempts WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()


def toggle_admin(user_id, is_admin):
    conn = get_connection()
    conn.execute("UPDATE users SET is_admin = ? WHERE id = ?", (is_admin, user_id))
    conn.commit()
    conn.close()


def update_user_profile(user_id, full_name, email, nt_id="", department="", team="", years_of_experience=0):
    conn = get_connection()
    conn.execute(
        "UPDATE users SET full_name = ?, email = ?, nt_id = ?, department = ?, team = ?, years_of_experience = ? WHERE id = ?",
        (full_name, email, nt_id, department, team, years_of_experience, user_id),
    )
    conn.commit()
    conn.close()


def change_password(user_id, new_password):
    conn = get_connection()
    salt, pw_hash = hash_password(new_password)
    conn.execute("UPDATE users SET password_hash = ?, salt = ? WHERE id = ?", (pw_hash, salt, user_id))
    conn.commit()
    conn.close()


# ── Skill operations ─────────────────────────────────────────────

def get_user_skills(user_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM user_skills WHERE user_id = ? ORDER BY topic", (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def set_self_rated_level(user_id, topic, level):
    conn = get_connection()
    conn.execute("""
        INSERT INTO user_skills (user_id, topic, self_rated_level, validated_level)
        VALUES (?, ?, ?, 0)
        ON CONFLICT(user_id, topic) DO UPDATE SET self_rated_level = ?
    """, (user_id, topic, level, level))
    conn.commit()
    conn.close()


def validate_skill_level(user_id, topic, level):
    conn = get_connection()
    conn.execute("""
        INSERT INTO user_skills (user_id, topic, self_rated_level, validated_level)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id, topic) DO UPDATE SET validated_level = ?
    """, (user_id, topic, level, level, level))
    conn.commit()
    conn.close()


def get_validated_level(user_id, topic):
    conn = get_connection()
    row = conn.execute(
        "SELECT validated_level FROM user_skills WHERE user_id = ? AND topic = ?",
        (user_id, topic),
    ).fetchone()
    conn.close()
    return row["validated_level"] if row else 0


# ── Quiz operations ──────────────────────────────────────────────

def save_quiz_attempt(user_id, topic, level, score, total_questions, passed):
    conn = get_connection()
    conn.execute(
        "INSERT INTO quiz_attempts (user_id, topic, level, score, total_questions, passed) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, topic, level, score, total_questions, passed),
    )
    conn.commit()
    conn.close()


def get_quiz_history(user_id, topic=None):
    conn = get_connection()
    if topic:
        rows = conn.execute(
            "SELECT * FROM quiz_attempts WHERE user_id = ? AND topic = ? ORDER BY attempted_at DESC",
            (user_id, topic),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM quiz_attempts WHERE user_id = ? ORDER BY attempted_at DESC",
            (user_id,),
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
