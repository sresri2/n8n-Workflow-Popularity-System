import sqlite3
import json
from datetime import datetime

DB_PATH = "workflow_trends.db"

def init_db():
    """
    Initialize the database by creating the 'workflow_trends' table if it does not exist.
    Columns:
      - id: primary key, auto-incremented
      - source: identifies the data source (google, youtube, forum)
      - term: search term (for Google Trends)
      - workflow: workflow title (for YouTube/forum)
      - platform: platform name, e.g., "YouTube" or "Forum"
      - metrics_json: JSON string storing popularity metrics or trend metrics
      - created_at: timestamp of insertion, defaults to current time
    """
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
    Insert workflow trend results into the database.
    
    Behavior:
      - Atomically replace all rows for a given source with new results.
      - Uses a transaction to ensure either all rows are replaced or none on failure.
    
    Parameters:
      - source: str, the source of the data ("google", "youtube", "forum")
      - results: list of dicts, each dict contains:
          - term (optional): search term (for Google Trends)
          - workflow (optional): workflow title (for YouTube/forum)
          - platform (optional): platform name
          - metrics or popularity_metrics: dict of metrics (views, likes, etc.)
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

