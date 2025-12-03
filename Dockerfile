FROM python:3.11-slim

# 1️⃣ Install system dependencies for pyodbc (SQL Server / Azure SQL)
RUN apt-get update && apt-get install -y \
    unixodbc \
    unixodbc-dev \
    libgssapi-krb5-2 \
    curl \
    gnupg \
    apt-transport-https \
    && rm -rf /var/lib/apt/lists/*

# 2️⃣ Set working directory
WORKDIR /app

# 3️⃣ Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4️⃣ Copy the rest of your app
COPY . .

# 5️⃣ Start FastAPI using Gunicorn + Uvicorn worker
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "-k", "uvicorn.workers.UvicornWorker", "main:app"]
