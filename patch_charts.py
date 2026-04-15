import re

with open('dream_dashboard.py', 'r') as f:
    content = f.read()

new_ui = """
# ---- 1A. Skill Evaluation Metrics ----
st.header("1A. Skill Evaluation Metrics")
query_results = f"SELECT skill_name, passed, failed FROM `{config['bigquery']['project_id']}.{config['bigquery']['dataset_id']}.dream_eval_results`"
try:
    results_df = bq_client.query(query_results).to_dataframe()
    if not results_df.empty:
        results_df['success_rate'] = (results_df['passed'] / (results_df['passed'] + results_df['failed']) * 100).fillna(0)
        st.bar_chart(results_df.set_index('skill_name')['success_rate'])
        st.write("Current Evaluation results:")
        st.dataframe(results_df, use_container_width=True)
    else:
        st.info("No eval metric results available.")
except Exception as e:
    st.error(f"Could not load eval metrics: {e}")

# ---- 2. Dream Epiphanies
"""

content = content.replace("# ---- 2. Dream Epiphanies & Token Waste Analysis ----", new_ui + "# ---- 2. Dream Epiphanies & Token Waste Analysis ----")

with open('dream_dashboard.py', 'w') as f:
    f.write(content)
