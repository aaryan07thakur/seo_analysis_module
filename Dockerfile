FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN apt-get update && apt-get install -y libxml2-dev libxslt-dev

# Copy entire project (not just `app`)
COPY . .

# Expose the FastAPI default port
EXPOSE 8000

# FastAPI command (will be overridden in docker-compose for Celery)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
