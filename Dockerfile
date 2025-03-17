# ✅ Use a lightweight Python image
FROM python:3.10-slim AS builder

# ✅ Set the working directory
WORKDIR /app

# ✅ Install system dependencies & PostgreSQL client
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ✅ Copy and install dependencies first (optimized caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ✅ Ensure Gunicorn is installed & print version
RUN python -m pip install --no-cache-dir gunicorn && gunicorn --version

# ✅ Second stage - Only copy necessary files
FROM python:3.10-slim
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.10 /usr/local/lib/python3.10
COPY . .

# ✅ Expose the port for Django
EXPOSE 8000

# ✅ Run migrations & collect static files on startup
RUN python manage.py migrate --noinput
RUN python manage.py collectstatic --noinput

# ✅ Start Gunicorn with more workers & timeout fixes
CMD ["gunicorn", "--workers=3", "--timeout=120", "--worker-class=gevent", "--bind", "0.0.0.0:8000", "farming_ai.wsgi:application"]
