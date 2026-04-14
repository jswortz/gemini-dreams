import sys
import json
import os
import subprocess
import sqlite3
import time
from datetime import datetime

def simulate_hook_call(prompt, response, agent_name="gemini_cli"):
    hook_path = os.path.join(os.getcwd(), "gemini-dreams-system/native_log_hook.py")
    payload = {
        "prompt": prompt,
        "prompt_response": response,
        "session_id": f"test-session-{agent_name}-123"
    }
    
    env = os.environ.copy()
    env["GEMINI_PROJECT_DIR"] = os.getcwd() # Simulate project context
    env["PYTHONPATH"] = os.path.join(os.getcwd(), "gemini-dreams-system") # For config_loader
    
    process = subprocess.Popen(
        ["python3", hook_path, agent_name],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env
    )
    stdout, stderr = process.communicate(input=json.dumps(payload))
    return stdout, stderr

def main():
    print("🚀 Starting Automated Hook & Dream Validation...")
    
    # 1. Simulate conversations for gemini_cli
    print("📝 Simulating gemini_cli interactions...")
    gemini_conversations = [
        ("How do I use the antigravity skill?", "To use antigravity, you need to call the activate_skill tool with 'antigravity'. Summary: Explained antigravity."),
        ("It's not working, it says 'unknown command'.", "I apologize, use 'activate_skill'. Summary: Corrected instructions.")
    ]
    
    for q, a in gemini_conversations:
        stdout, stderr = simulate_hook_call(q, a, "gemini_cli")
        if stderr: print(f"❌ Hook error: {stderr}")
        else: print(f"✅ gemini_cli hook allowed: {stdout.strip()}")

    # 2. Simulate conversations for jetski
    print("\n📝 Simulating jetski interactions...")
    jetski_conversations = [
        ("Refactor this class to use composition.", "I have refactored the class to use composition instead of inheritance. Summary: Refactored code with jetski."),
        ("Add tests for the new class.", "I've added unit tests for the newly refactored class. Summary: Added tests with jetski.")
    ]
    
    for q, a in jetski_conversations:
        stdout, stderr = simulate_hook_call(q, a, "jetski")
        if stderr: print(f"❌ Hook error: {stderr}")
        else: print(f"✅ jetski hook allowed: {stdout.strip()}")

    # 3. Verify log files exist and have content
    log_files = {
        "gemini_cli": os.path.expanduser("~/.gemini/sessions/gemini_cli_history.jsonl"),
        "jetski": os.path.expanduser("~/.jetski/sessions/jetski_history.jsonl")
    }
    
    for agent, path in log_files.items():
        if os.path.exists(path):
            print(f"📂 Log file found for {agent} at {path}")
            with open(path, 'r') as f:
                lines = f.readlines()
                print(f"📊 {agent} logged {len(lines)} lines.")
                last_entry = json.loads(lines[-1])
                print(f"✨ Latency: {last_entry.get('latency_ms')}ms, Skills: {last_entry.get('skills')}")
        else:
            print(f"❌ Log file for {agent} NOT found at {path}")
            # Don't exit yet, check config
            
    # 4. Run the Dream Runner
    print("\n💤 Running Nightly Dream Analysis (Dream Runner)...")
    if os.path.exists("state.json"): os.remove("state.json")
    
    # Use standard config but ensure we check multiple agents
    subprocess.run(["python3", "gemini-dreams-system/dream_runner.py"], check=True)

    # 5. Validate epiphanies in SQLite
    # Load config to find DB
    from config_loader import load_config
    config = load_config()
    db_path = os.path.expanduser(config["db_path"])
    
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("SELECT session_id, epiphanies FROM session_analysis ORDER BY timestamp DESC")
        rows = c.fetchall()
        if rows:
            print(f"🧠 Found {len(rows)} Dream Epiphanies.")
            for row in rows[:2]:
                print(f"  - {row[0]}: {row[1][:60]}...")
            print("✅ Dream Epiphany validation passed!")
        else:
            print("❌ No epiphanies found in database!")
            sys.exit(1)
        conn.close()
    else:
        print(f"❌ Database NOT found at {db_path}!")
        sys.exit(1)

    print("\n🏁 Full Validation Suite Complete!")

if __name__ == "__main__":
    main()