FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY . .

EXPOSE 6000

CMD ["gunicorn", "--bind", "0.0.0.0:6000", "--workers", "1", "--threads", "8", "--timeout", "3600", "app:app"]
