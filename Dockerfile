FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY *.py .

CMD ["python3", "main.py", "--topic", "machine learning", "--days", "7", "--limit", "50"]
