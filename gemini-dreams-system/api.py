import sqlite3
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Enable CORS so the Vite frontend can access it
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GEMINI_DIR = os.path.expanduser("~/.gemini")
DREAM_METRICS_DB = os.path.join(GEMINI_DIR, "dream_metrics.db")

def get_db_connection():
    conn = sqlite3.connect(DREAM_METRICS_DB)
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/api/coverage")
async def get_coverage():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT timestamp, skill_name, has_evals FROM eval_coverage ORDER BY timestamp DESC")
        rows = cursor.fetchall()
        conn.close()
        
        # Convert rows to list of dicts
        return [dict(row) for row in rows]
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/dreams")
async def get_dreams():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT timestamp, session_id, turn_count, epiphanies, skill_updates,
                   latency_before, latency_after, tokens_before, tokens_after 
            FROM session_analysis 
            ORDER BY timestamp DESC LIMIT 20
        """)
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
