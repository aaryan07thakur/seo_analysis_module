# SEO Scanner API

A FastAPI backend service that performs SEO scanning on websites. The service uses Celery for asynchronous task processing and Redis as a message broker and result backend.

## Features

- Scan URLs for SEO metrics and issues
- Asynchronous processing with Celery
- Result storage and retrieval
- RESTful API endpoints

## Prerequisites

- Python 3.8+
- Redis server

## Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/seo-scanner-api.git
cd seo-scanner-api
```

2. Create a virtual environment and activate it:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install the dependencies:

```bash
pip install -r requirements.txt
```

## Configuration

Ensure Redis is running on your machine. By default, the application connects to Redis at `redis://localhost:6379/0`. If your Redis instance is running elsewhere, modify the connection settings in the configuration files.

## Running the Application

### Start Redis (if not already running)

```bash
# On most systems
redis-server

# On Windows (if installed via WSL)
sudo service redis-server start
```

### Start Celery Worker

```bash
celery -A celery_worker worker --loglevel=info
```

### Start FastAPI Application

```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`.

## API Documentation

After starting the application, you can access the interactive API documentation at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## API Endpoints

### 1. Scan URL

Initiates an SEO scan for the provided URL.

- **URL**: `/start-analysis`
- **Method**: `POST`
- **Request Body**:
  ```json
  {
    "url": "https://example.com"
  }
  ```
- **Response**:
  ```json
  {
    "id": "task-uuid-here",
    "status": "processing",
    "result": {},
  }
  ```

### 2. Get Scan Results

Retrieves the results of a previously initiated scan.
Use the id obtained from "/start-analysis" as scan_id (/get-analysis/task-uuid-here)

- **URL**: `/get-analysis/{scan_id}` 
- **Method**: `GET`
- **Response**:
  ```json
        {
            "id": "task-uuid-here",
            "status": "processing",
            "result": {},
        }
  ```

For any questions or support, please open an issue in the GitHub repository.