FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    gettext \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/

RUN date +%s > /app/.build_date

RUN DJANGO_SECRET_KEY=build-only ALLOW_INSECURE_SECRET=1 DATABASE_URL=sqlite:///tmp/build.sqlite python manage.py compilemessages

RUN DJANGO_SECRET_KEY=build-only ALLOW_INSECURE_SECRET=1 DATABASE_URL=sqlite:///tmp/build.sqlite python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn letterbookd.wsgi:application --bind 0.0.0.0:8000"]
