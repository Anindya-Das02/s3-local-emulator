FROM python:3.12.9-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY main.py main.py
COPY s3_downloads s3_downloads

EXPOSE 8773

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8773"]