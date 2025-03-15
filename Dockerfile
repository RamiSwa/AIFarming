# ✅ Use a lightweight Python image
FROM python:3.10-slim

# ✅ Set the working directory
WORKDIR /app

# ✅ Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# ✅ Copy and install dependencies first (optimized caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ✅ Copy the project files (except .env)
COPY . .

# ✅ Expose the port for Django
EXPOSE 8000

# ✅ Run migrations & collect static files on startup
RUN python manage.py migrate --noinput
RUN python manage.py collectstatic --noinput

# ✅ Use Gunicorn for production
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "farming_ai.wsgi:application"]
