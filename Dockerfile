FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt gunicorn

COPY backend/ ./backend/
COPY frontend/ ./frontend/

WORKDIR /app/backend

RUN SECRET_KEY=build-time-secret DEBUG=False python manage.py collectstatic --noinput --clear

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "strategem.wsgi:application"]
