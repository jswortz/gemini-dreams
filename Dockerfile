FROM node:22-slim AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --registry https://registry.npmjs.org
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim
WORKDIR /app
COPY api.py config.json ./
COPY --from=frontend /build/dist ./frontend/dist
RUN pip install --no-cache fastapi uvicorn google-cloud-bigquery
EXPOSE 8080
CMD ["python", "api.py"]
