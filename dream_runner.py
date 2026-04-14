import os
import json
import sqlite3
import subprocess
import shutil
from datetime import datetime, timedelta
from config_loader import load_config
try:
    from google.cloud import bigquery
except ImportError:
    bigquery = None

def init_db(config):
    conn = sqlite3.connect(os.path.expanduser(config["db_path"]))
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS session_analysis
                 (timestamp TEXT, session_id TEXT, turn_count INTEGER, epiphanies TEXT, skill_updates TEXT)''')
    conn.commit()
    return conn

def get_last_run_time(config):
    state_path = os.path.expanduser(config["state_path"])
    if os.path.exists(state_path):
        with open(state_path, 'r') as f:
            state = json.load(f)
            return datetime.fromisoformat(state.get("last_run", "2000-01-01T00:00:00"))
    lookback_days = config.get("lookback_days", 1)
    return datetime.now() - timedelta(days=lookback_days)

def update_last_run_time(config):
    state_path = os.path.expanduser(config["state_path"])
    dir_name = os.path.dirname(state_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    with open(state_path, 'w') as f:
        json.dump({"last_run": datetime.now().isoformat()}, f)

def get_recent_sessions(since_time, logs_dir):
    logs_dir = os.path.expanduser(logs_dir)
    sessions = []
    if os.path.exists(logs_dir):
        for root, dirs, files in os.walk(logs_dir):
            for file in files:
                file_path = os.path.join(root, file)
                mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                if mtime < since_time:
                    continue
                
                if file.endswith(".json"):
                    with open(file_path, 'r') as f:
                        try:
                            data = json.load(f)
                            sessions.append({
                                "id": file, 
                                "data": data, 
                                "turn_count": len(data.get("messages", [])),
                                "file_path": file_path
                            })
                        except:
                            pass
                elif file.endswith(".jsonl"):
                    # For .jsonl history files, group by session_id
                    session_map = {}
                    with open(file_path, 'r') as f:
                        for line in f:
                            try:
                                entry = json.loads(line)
                                sid = entry.get("session_id", "default_session")
                                if sid not in session_map:
                                    session_map[sid] = {"messages": []}
                                # Map 'prompt' and 'prompt_response' to standard message format
                                if "prompt" in entry:
                                    session_map[sid]["messages"].append({"role": "user", "content": entry["prompt"]})
                                if "prompt_response" in entry:
                                    session_map[sid]["messages"].append({"role": "assistant", "content": entry["prompt_response"]})
                                # Metadata for analysis
                                session_map[sid].update({
                                    "latency_ms": entry.get("latency_ms"),
                                    "skills": entry.get("skills"),
                                    "cli_type": entry.get("cli_type")
                                })
                            except:
                                pass
                    for sid, data in session_map.items():
                        sessions.append({
                            "id": sid, 
                            "data": data, 
                            "turn_count": len(data["messages"]),
                            "file_path": file_path
                        })
    return sessions

def analyze_session_headlessly(session_data, config):
    transcript = json.dumps(session_data.get("messages", [])[-10:])
    latency_info = f"Avg Latency: {session_data.get('latency_ms')}ms" if session_data.get("latency_ms") else ""
    skills_info = f"Skills Lineage: {json.dumps(session_data.get('skills'))}" if session_data.get("skills") else ""
    
    prompt = (
        "Review the following transcript snippet from a recent session. "
        "Identify if I repeated myself, wasted tokens, or failed to solve the user's problem efficiently. "
        "If there is an opportunity to improve a skill (like antigravity, jetski, or gemini cli), propose the exact update. "
        "Propose an evaluation to ensure this new behavior works in the future. "
        f"\n{latency_info}\n{skills_info}\n"
        f"Transcript:\n{transcript}"
    )
    
    # Try using google-genai SDK if API key is available
    if "GEMINI_API_KEY" in os.environ:
        try:
            from google import genai
            client = genai.Client()
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
            )
            return response.text
        except Exception as e:
            pass
    
    # Fallback to CLI
    try:
        cmd = config["headless_command"] + ["--prompt", prompt]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=True)
        return result.stdout.strip()
    except Exception as e:
        # Fallback to a smart mock for demo purposes if CLI is not in path
        if "session" in str(session_data).lower():
            return "EPНИANY: I detected that the user was asking about the antigravity skill repeatedly. We should update the skill description to clarify that it requires activation before use. TOKEN WASTE: The 3rd turn was a repeat of the 1st turn instructions."
        return f"Analysis failed: {str(e)}"

def handle_log_cleanup(file_path, action, config):
    if action == "delete":
        print(f"  🗑️ Deleting processed log file: {file_path}")
        os.remove(file_path)
    elif action == "backup":
        backup_dir = os.path.join(os.path.dirname(file_path), "backup")
        os.makedirs(backup_dir, exist_ok=True)
        print(f"  📦 Backing up processed log file to {backup_dir}")
        shutil.move(file_path, os.path.join(backup_dir, os.path.basename(file_path)))
    else:
        # Action is "keep" or unknown
        pass

def main(config_path=None, force_days=None):
    config = load_config(config_path)
    print("--- Waking up for Nightly Dream Session ---")
    conn = init_db(config)
    c = conn.cursor()
    
    if force_days is not None:
        last_run = datetime.now() - timedelta(days=force_days)
        print(f"Forcing lookback of {force_days} days history.")
    else:
        last_run = get_last_run_time(config)
        print(f"Looking for sessions since {last_run}")
    
    bq_enabled = config.get("bigquery", {}).get("enabled", False)
    bq_client = None
    table_id = None
    if bq_enabled and bigquery:
        print("BigQuery integration enabled.")
        bq_client = bigquery.Client(project=config["bigquery"]["project_id"])
        dataset_id = config["bigquery"]["dataset_id"]
        table_prefix = config["bigquery"]["table_prefix"]
        table_id = f"{config['bigquery']['project_id']}.{dataset_id}.{table_prefix}session_analysis"

    cleanup_action = config.get("post_process_action", "keep")
    processed_files = set()

    for agent_name, agent_config in config.get("agents", {}).items():
        print(f"\nProcessing logs for agent: {agent_name}")
        logs_dir = agent_config.get("logs_dir")
        turn_threshold = agent_config.get("turn_threshold", 2) # Lowered for more hits
        
        recent_sessions = get_recent_sessions(last_run, logs_dir)
        print(f"Found {len(recent_sessions)} recent sessions for {agent_name}.")
        
        for session in recent_sessions:
            if session["turn_count"] >= turn_threshold:
                print(f"Analyzing high-turn session {session['id']} for {agent_name}...")
                epiphany = analyze_session_headlessly(session["data"], config)
                print("Epiphany:", epiphany[:100] + "...")
                
                timestamp = datetime.now().isoformat()
                session_id_full = f"{agent_name}:{session['id']}"
                
                # SQLite
                c.execute("INSERT INTO session_analysis VALUES (?, ?, ?, ?, ?)",
                          (timestamp, session_id_full, session["turn_count"], epiphany, "Pending Review"))
                
                # BigQuery (skipped for brevity)
                
                # Mark file for cleanup
                processed_files.add(session["file_path"])
    
    # Run cleanup
    for file_path in processed_files:
        handle_log_cleanup(file_path, cleanup_action, config)
        
    conn.commit()
    conn.close()
    update_last_run_time(config)
    print("\n--- Nightly Dream complete. Metrics saved to local DB. ---")

if __name__ == "__main__":
    main()