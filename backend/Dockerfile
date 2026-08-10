FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    poppler-utils \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY . /app/backend/

WORKDIR /app/backend

ENV CHROMA_PATH=/app/chroma_db

EXPOSE 8000

CMD ["gunicorn", "run:app", "-w", "2", "--threads", "8", "--worker-class", "gthread", "--timeout", "120", "-b", "0.0.0.0:8000"]
