import sqlite3
from fastapi import FastAPI
from typing import List, Dict, Any

DB_PATH = "workflow_trends.db"
TOP_LIMIT = 20

app = FastAPI(title="Workflow Trends API")


def score_forum(popularity_metrics: dict) -> float:
    """
    Combine forum metrics into a single popularity score.
    - Views: baseline weight
    - Replies: weighted more since it means engagement
    - Likes: weighted similarly to replies
    - Unique contributors: strong indicator of discussion quality
    """
    views = popularity_metrics.get("views", 0)
    replies = popularity_metrics.get("replies", 0)
    likes = popularity_metrics.get("likes", 0)
    contributors = popularity_metrics.get("unique_contributors", 0)

    score = (
        (views * 1.0) +           
        (replies * 20.0) +        
        (likes * 10.0) +         
        (contributors * 30.0)    
    )
    return score


def score_google(metrics: dict) -> float:
    """
    Combine avg_interest, latest_interest, and trend.
    Weight latest interest slightly more than average.
    Give a small bonus/penalty for trend.
    """
    avg_interest = metrics.get("avg_interest", 0)
    latest_interest = metrics.get("latest_interest", 0)
    trend = metrics.get("trend", "stable")

    trend_bonus = 0
    if trend == "up":
        trend_bonus = 10  
    elif trend == "down":
        trend_bonus = -5  

    score = (avg_interest * 0.4) + (latest_interest * 0.6) + trend_bonus
    return score


def score_youtube(popularity_metrics: dict) -> float:
    """
    Combine YouTube metrics fairly.
    Views are baseline, likes and comments have stronger weight.
    Ratios (like_to_view, comment_to_view) normalize engagement.
    """
    views = popularity_metrics.get("views", 0)
    likes = popularity_metrics.get("likes", 0)
    comments = popularity_metrics.get("comments", 0)
    like_ratio = popularity_metrics.get("like_to_view_ratio", 0)
    comment_ratio = popularity_metrics.get("comment_to_view_ratio", 0)

    score = (
        (views * 1.0) +
        (likes * 20.0) +
        (comments * 30.0) +
        (like_ratio * 5000) +     
        (comment_ratio * 8000)   
    )
    return score


def query_db(query: str, params=()) -> list[dict]:
    """
    Run a query on SQLite database and return results as a list of dictionaries.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.get("/")
def root():
    """Basic health check route."""
    return {"status": "ok", "message": "Workflow Trends API is running."}

@app.get("/google")
def get_google_workflows():
    rows = query_db("SELECT * FROM workflow_trends WHERE source = 'google'")
    for row in rows:
        row["popularity_score"] = score_google(eval(row["metrics_json"]))
    sorted_rows = sorted(rows, key=lambda r: r["popularity_score"], reverse=True)
    top_rows = sorted_rows[:TOP_LIMIT]
    return {"source": "google", "count": len(top_rows), "results": top_rows}

@app.get("/forum")
def get_forum_workflows():
    rows = query_db("SELECT * FROM workflow_trends WHERE source = 'forum'")
    for row in rows:
        row["popularity_score"] = score_forum(eval(row["metrics_json"]))
    sorted_rows = sorted(rows, key=lambda r: r["popularity_score"], reverse=True)
    top_rows = sorted_rows[:TOP_LIMIT]
    return {"source": "forum", "count": len(top_rows), "results": top_rows}

@app.get("/youtube")
def get_youtube_workflows():
    rows = query_db("SELECT * FROM workflow_trends WHERE source = 'youtube'")
    for row in rows:
        row["popularity_score"] = score_youtube(eval(row["metrics_json"]))
    sorted_rows = sorted(rows, key=lambda r: r["popularity_score"], reverse=True)
    return {"source": "youtube", "count": len(sorted_rows), "results": sorted_rows}

@app.get("/all")
def get_all_sources():
    return {
        "google": get_google_workflows(),
        "forum": get_forum_workflows(),
        "youtube": get_youtube_workflows()
    }
