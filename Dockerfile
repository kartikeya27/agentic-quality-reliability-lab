FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir . && useradd -r -u 10001 demo
USER demo
ENV AQ_MODE=deterministic PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["uvicorn", "agent_quality_lab.api:app", "--host", "0.0.0.0", "--port", "8000"]
