import sqlite3
import pandas as pd
import streamlit as st
import os

GEMINI_DIR = os.path.expanduser("~/.gemini")
DREAM_METRICS_DB = os.path.join(GEMINI_DIR, "dream_metrics.db")

st.set_page_config(page_title="Gemini Nightly Dream Dashboard", layout="wide")

st.title("🌙 Gemini Nightly Dream Dashboard")
st.markdown("Metrics and epiphanies generated from the self-aware agent eval sessions.")

import json

def load_config():
    try:
        with open("config.json", "r") as f:
            return json.load(f)
    except Exception:
        return {"bigquery": {"project_id": "wortz-project-352116", "dataset_id": "gemini_dreams"}}

def load_data(query):
    try:
        config = load_config()
        from google.cloud import bigquery
        client = bigquery.Client(project=config["bigquery"]["project_id"])
        
        # Rewrite query slightly if needed, assuming BQ dataset
        dataset_id = config["bigquery"]["dataset_id"]
        table_prefix = config.get("bigquery", {}).get("table_prefix", "dream_")
        
        # Replace table names with BQ table names
        bq_query = query.replace("eval_coverage", f"{dataset_id}.{table_prefix}eval_coverage")
        bq_query = bq_query.replace("session_analysis", f"{dataset_id}.{table_prefix}session_analysis")
        
        df = client.query(bq_query).to_dataframe()
        return df
    except Exception as e:
        st.error(f"Failed to load data: {e}")
        return pd.DataFrame()

# ---- 1. Eval Coverage ----
st.header("1. Skill Evaluation Coverage")
coverage_df = load_data("SELECT timestamp, skill_name, has_evals FROM eval_coverage ORDER BY timestamp DESC LIMIT 50")
if not coverage_df.empty:
    # Deduplicate to show latest state per skill
    latest_coverage = coverage_df.drop_duplicates(subset=['skill_name'], keep='first')
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="Total Skills Monitored", value=len(latest_coverage))
        st.metric(label="Skills with Evals", value=int(latest_coverage['has_evals'].sum()))
    
    with col2:
        st.dataframe(latest_coverage[['skill_name', 'has_evals']].style.applymap(
            lambda x: 'background-color: lightgreen' if x == 1 else 'background-color: lightcoral', subset=['has_evals']
        ))
else:
    st.info("No coverage data available. Ensure eval_checker.py is running.")


def load_config_bq():
    import json
    try:
        with open("config.json", "r") as f:
            return json.load(f)
    except Exception:
        return {"bigquery": {"project_id": "wortz-project-352116", "dataset_id": "gemini_dreams"}}

# ---- 1A. Skill Evaluation Metrics ----
st.header("1A. Skill Evaluation Metrics")
bq_conf = load_config_bq()
query_results = f"SELECT skill_name, passed, failed FROM `{bq_conf['bigquery']['project_id']}.{bq_conf['bigquery']['dataset_id']}.dream_eval_results`"
try:
    from google.cloud import bigquery
    client = bigquery.Client(project=bq_conf['bigquery']['project_id'])
    results_df = client.query(query_results).to_dataframe()
    if not results_df.empty:
        results_df['success_rate'] = (results_df['passed'] / (results_df['passed'] + results_df['failed']) * 100).fillna(0)
        st.bar_chart(results_df.set_index('skill_name')['success_rate'])
        st.write("Current Evaluation results:")
        st.dataframe(results_df, use_container_width=True)
    else:
        st.info("No eval metric results available.")
except Exception as e:
    st.error(f"Could not load eval metrics: {e}")


# ---- 2. Session Analysis (The "Dreams") ----
st.header("2. Dream Epiphanies & Token Waste Analysis")
analysis_df = load_data("SELECT timestamp, session_id, turn_count, epiphanies FROM session_analysis ORDER BY timestamp DESC LIMIT 10")

if not analysis_df.empty:
    st.write(f"Recent analyzed sessions: {len(analysis_df)}")
    for idx, row in analysis_df.iterrows():
        with st.expander(f"Session {row['session_id']} (Turns: {row['turn_count']}) - {row['timestamp']}"):
            st.markdown("**Agent's Epiphany / Proposed Skill Update:**")
            st.markdown(row['epiphanies'])
else:
    st.info("No dream sessions logged yet. Ensure dream_runner.py runs nightly.")

# ---- 3. Export to BigQuery Help ----
st.sidebar.header("Export Options")
st.sidebar.markdown("To push this data to BigQuery for long-term reporting:")
st.sidebar.code("python export_to_bq.py --dataset my_dataset", language="bash")
