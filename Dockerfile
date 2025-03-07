FROM python:3.12.9-slim

WORKDIR /app

COPY requirements.txt .

# RUN pip install --no-cache-dir -r requirements.txt

# workaround for SSLCertVerificationError, CERTIFICATE_VERIFY_FAILED error
RUN pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt

COPY main.py main.py
COPY s3_downloads s3_downloads

EXPOSE 8773

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8773"]