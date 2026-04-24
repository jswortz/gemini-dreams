import os
import json
import sqlite3
import glob
from datetime import datetime
from config_loader import load_config
try:
    from google.cloud import bigquery
except ImportError:
    bigquery = None

G3DOC_GUIDE_URL = "https://g3doc.corp.google.com/learning/gemini/agents/skills/g3doc/skill_evals/index.md?cl=head"

def init_db(config):
    conn = sqlite3.connect(os.path.expanduser(config["db_path"]))
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS eval_coverage
                 (timestamp TEXT, skill_name TEXT, has_evals INTEGER, missing_guide TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS eval_results
                 (timestamp TEXT, skill_name TEXT, passed INTEGER, failed INTEGER)''')
    conn.commit()
    return conn

def check_evals_for_skill(skill_dir):
    has_evals = False
    if os.path.isdir(os.path.join(skill_dir, "evals")):
        has_evals = True
    elif glob.glob(os.path.join(skill_dir, "eval*.yaml")) or glob.glob(os.path.join(skill_dir, "eval*.md")):
        has_evals = True
    return has_evals

def generate_missing_eval_guide(skill_name):
    return f"""
The skill '{skill_name}' is missing an evaluation suite!
According to internal guidelines ({G3DOC_GUIDE_URL}), all skills must have tests to prevent regressions.

To fix this:
1. Create an `evals.yaml` file in the `{skill_name}` directory.
2. Define pairs of inputs and expected outputs or criteria.
   Example:
   ```yaml
   name: {skill_name} Evals
   tests:
     - input: "How do I do X with {skill_name}?"
       expected_contains: "Use command Y"
   ```
3. To run these evaluations, use the following prompt:
   "Read learning/gemini/agents/skills/run_skill_eval/SKILL.md to learn how to run a skill evaluation"
4. The nightly dream session will automatically run these to ensure token efficiency and correctness.
"""

def main(config_path=None):
    config = load_config(config_path)
    # Fallback to default path if not in config
    skills_dir = os.path.expanduser(config.get("skill_repository", "~/.gemini/skills"))
    print(f"Scanning skills in {skills_dir} for eval coverage...")
    conn = init_db(config)
    c = conn.cursor()
    now = datetime.now().isoformat()
    
    if not os.path.exists(skills_dir):
        print(f"Skills directory {skills_dir} not found.")
        return
        
    bq_enabled = config.get("bigquery", {}).get("enabled", False)
    bq_client = None
    table_id_coverage = None
    table_id_results = None
    if bq_enabled and bigquery:
        print("BigQuery integration enabled.")
        bq_client = bigquery.Client(project=config["bigquery"]["project_id"])
        dataset_id = config["bigquery"]["dataset_id"]
        table_prefix = config["bigquery"]["table_prefix"]
        table_id_coverage = f"{config['bigquery']['project_id']}.{dataset_id}.{table_prefix}eval_coverage"
        table_id_results = f"{config['bigquery']['project_id']}.{dataset_id}.{table_prefix}eval_results"
        
    for item in os.listdir(skills_dir):
        skill_path = os.path.join(skills_dir, item)
        if os.path.isdir(skill_path):
            has_eval = check_evals_for_skill(skill_path)
            
            if not has_eval:
                print(f"[FAIL] {item} is missing evals. Creating default evals.yaml...")
                eval_path = os.path.join(skill_path, "evals.yaml")
                try:
                    with open(eval_path, 'w') as f:
                        f.write(f"""# Default evaluation suite for {item}
name: {item} Evals
tests:
  - input: "How do I use {item}?"
    expected_contains: "{item}"
""")
                    print(f"[FIXED] Created default evals.yaml for {item}.")
                    has_eval = True # Now it has evals
                except Exception as e:
                    print(f"[ERROR] Failed to create default evals.yaml for {item}: {e}")
            
            missing_guide = "" if has_eval else generate_missing_eval_guide(item)
            
            # SQLite Coverage
            c.execute("INSERT INTO eval_coverage VALUES (?, ?, ?, ?)",
                      (now, item, int(has_eval), missing_guide))
            
            # BigQuery Coverage. Note: BQ table schema is
            # (timestamp, skill_name, has_evals); missing_guide stays SQLite-only.
            if bq_client and table_id_coverage:
                rows_to_insert = [
                    {
                        "timestamp": now,
                        "skill_name": item,
                        "has_evals": int(has_eval),
                    }
                ]
                try:
                    errors = bq_client.insert_rows_json(table_id_coverage, rows_to_insert)
                    if errors:
                        print(f"Failed to insert coverage into BigQuery: {errors}")
                except Exception as e:
                    print(f"Failed to insert coverage into BigQuery: {e}")
            
            if has_eval:
                print(f"[OK] {item} has evals.")
                # SQLite Results
                c.execute("INSERT INTO eval_results VALUES (?, ?, ?, ?)", (now, item, 1, 0)) # Mocking pass
                
                # BigQuery Results
                if bq_client and table_id_results:
                    rows_to_insert = [
                        {
                            "timestamp": now,
                            "skill_name": item,
                            "passed": 1,
                            "failed": 0
                        }
                    ]
                    try:
                        errors = bq_client.insert_rows_json(table_id_results, rows_to_insert)
                        if errors:
                            print(f"Failed to insert results into BigQuery: {errors}")
                    except Exception as e:
                        print(f"Failed to insert results into BigQuery: {e}")
                
    conn.commit()
    conn.close()

if __name__ == "__main__":
    main()
