"""database.py — SQLite persistence for the Autonomous Job Research Agent.
Author: Avatar Putra Sigit | GitHub: qurrrrsebastian-prog
"""
import os
import sqlite3
from datetime import datetime
from typing import List, Optional

import pandas as pd

DB_PATH = os.path.join(os.path.dirname(__file__), "app.db")


def get_connection() -> sqlite3.Connection:
    """Return a SQLite connection with row access by name."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create tables. Call once at app start."""
    conn = get_connection()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS searches (
            id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT,
            role TEXT, location TEXT, level TEXT, queries_used TEXT,
            result_count INTEGER, demo_mode BOOLEAN, execution_time_seconds REAL);
        CREATE TABLE IF NOT EXISTS saved_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, search_id INTEGER,
            company_name TEXT, job_title TEXT, location TEXT, salary_hint TEXT,
            skill_match_score INTEGER, recommendation TEXT, saved_at TEXT);
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, user TEXT,
            action TEXT, details TEXT);
        """
    )
    conn.commit()
    conn.close()


def add_log(action: str, details: str = "", user: str = "anonymous") -> None:
    """Append an entry to the audit log."""
    conn = get_connection()
    conn.execute(
        "INSERT INTO audit_log (timestamp, user, action, details) VALUES (?, ?, ?, ?)",
        (datetime.now().isoformat(timespec="seconds"), user, action, details),
    )
    conn.commit()
    conn.close()


# --------------------------------------------------------------------------- #
# Searches
# --------------------------------------------------------------------------- #
def add_search(role: str, location: str, level: str, queries_used: str,
               result_count: int, demo_mode: bool,
               execution_time_seconds: float) -> int:
    """Record a search and return its id."""
    conn = get_connection()
    cur = conn.execute(
        """INSERT INTO searches
           (timestamp, role, location, level, queries_used, result_count,
            demo_mode, execution_time_seconds)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (datetime.now().isoformat(timespec="seconds"), role, location, level,
         queries_used, result_count, 1 if demo_mode else 0, execution_time_seconds),
    )
    conn.commit()
    rid = cur.lastrowid
    conn.close()
    return rid


def get_searches(limit: int = 200) -> pd.DataFrame:
    """Return search history, newest first."""
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT * FROM searches ORDER BY id DESC LIMIT ?", conn, params=[limit])
    conn.close()
    return df


def clear_searches() -> None:
    """Delete all search history."""
    conn = get_connection()
    conn.execute("DELETE FROM searches")
    conn.commit()
    conn.close()


# --------------------------------------------------------------------------- #
# Saved jobs
# --------------------------------------------------------------------------- #
def save_job(job: dict, search_id: Optional[int] = None) -> None:
    """Bookmark a job (de-duplicated on company + title)."""
    conn = get_connection()
    exists = conn.execute(
        "SELECT id FROM saved_jobs WHERE company_name=? AND job_title=?",
        (job.get("company_name", ""), job.get("job_title", "")),
    ).fetchone()
    if exists is None:
        conn.execute(
            """INSERT INTO saved_jobs
               (search_id, company_name, job_title, location, salary_hint,
                skill_match_score, recommendation, saved_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (search_id, job.get("company_name", ""), job.get("job_title", ""),
             job.get("location", ""), job.get("salary_hint", ""),
             int(job.get("skill_match_score", 0) or 0),
             job.get("recommendation", ""),
             datetime.now().isoformat(timespec="seconds")),
        )
        conn.commit()
    conn.close()


def get_saved_jobs() -> pd.DataFrame:
    """Return all bookmarked jobs, newest first."""
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM saved_jobs ORDER BY id DESC", conn)
    conn.close()
    return df


def delete_saved_job(job_id: int) -> None:
    """Remove a bookmarked job by id."""
    conn = get_connection()
    conn.execute("DELETE FROM saved_jobs WHERE id = ?", (job_id,))
    conn.commit()
    conn.close()


def saved_count() -> int:
    """Return the number of bookmarked jobs."""
    conn = get_connection()
    n = conn.execute("SELECT COUNT(*) AS c FROM saved_jobs").fetchone()["c"]
    conn.close()
    return int(n)
