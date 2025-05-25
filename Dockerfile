# Dockerfile voor jouw Flask API
FROM python:3.13.3-slim

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5000

CMD ["python", "api.py"]
