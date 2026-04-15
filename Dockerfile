FROM python:3.11-slim
WORKDIR /app
COPY . /app
RUN pip install --no-cache streamlit pandas db-dtypes google-cloud-bigquery
EXPOSE 8080
CMD ["streamlit", "run", "dream_dashboard.py", "--server.port=8080", "--server.address=0.0.0.0"]
