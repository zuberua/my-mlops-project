FROM public.ecr.aws/docker/library/python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY agent/ ./agent/
COPY agentcore_app.py .

EXPOSE 8080

CMD ["python", "agentcore_app.py"]
