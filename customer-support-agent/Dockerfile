FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY agent/ ./agent/
COPY agentcore_app.py .

ENV PYTHONUNBUFFERED=1
ENV AWS_DEFAULT_REGION=us-west-2
ENV AWS_REGION=us-west-2
ENV DYNAMODB_TABLE_NAME=markvie-kb-poc
ENV TASK_SUMMARY_TABLE_NAME=markvie-kb-task-summaries-poc

EXPOSE 8080

CMD ["python", "agentcore_app.py"]
