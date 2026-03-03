FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY config/ ./config/
COPY agent.py .
COPY agentcore_app.py .
COPY plc_diagram_generator.py .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV AWS_DEFAULT_REGION=us-west-2

# Expose port for AgentCore
EXPOSE 8080

# Run the AgentCore app
CMD ["python", "-m", "strands.agentcore", "agentcore_app:app"]

