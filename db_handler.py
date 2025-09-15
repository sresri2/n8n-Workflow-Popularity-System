import sqlite3
import json
from datetime import datetime

DB_PATH = "workflow_trends.db"

def init_db():
    """Initialize database and create table if not exists."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS workflow_trends (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,        -- google, youtube, forum
            term TEXT,                   -- search term (for Google Trends)
            workflow TEXT,               -- workflow title (for YT/forum)
            platform TEXT,               -- e.g. YouTube, Forum
            metrics_json TEXT NOT NULL,  -- store popularity or trend metrics as JSON
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def insert_results(source, results):
    """
    Atomically replace rows for this source with new results.
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    try:
        cur.execute("BEGIN")
        
        cur.execute("DELETE FROM workflow_trends WHERE source = ?", (source,))
        
        for r in results:
            term = r.get("term")
            workflow = r.get("workflow")
            platform = r.get("platform")
            metrics = json.dumps(r.get("metrics") or r.get("popularity_metrics"))
            cur.execute("""
                INSERT INTO workflow_trends (source, term, workflow, platform, metrics_json)
                VALUES (?, ?, ?, ?, ?)
            """, (source, term, workflow, platform, metrics))
        
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

