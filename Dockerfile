FROM python:3.13-slim

# не створювати .pyc і одразу виводити логи
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# спочатку тільки requirements - так docker закешує встановлені пакети
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# збираємо статику для whitenoise (ключ тут тимчасовий, тільки для збірки)
RUN DJANGO_SECRET_KEY=build-only-key python manage.py collectstatic --noinput

# запускаємо не від root - так безпечніше
RUN useradd --create-home appuser \
    && mkdir -p /app/data /app/media \
    && chown -R appuser /app
USER appuser

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--access-logfile", "-"]
