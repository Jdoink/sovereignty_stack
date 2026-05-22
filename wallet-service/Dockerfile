FROM python:3.11-slim

# argon2-cffi and cryptography need build tools on slim
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential \
      libffi-dev \
      libssl-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py ./

ENV PYTHONUNBUFFERED=1

EXPOSE 8788

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8788"]
