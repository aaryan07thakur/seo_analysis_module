from fastapi import FastAPI
from app.routers import router  # Import the router from routers.py
from app.logger_config import logger

app = FastAPI()

# Include the router with an optional prefix
app.include_router(router, prefix="/api/v1")



if __name__ == "__main__":
    import uvicorn
    logger.info("Starting App.....")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)