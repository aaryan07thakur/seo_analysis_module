from fastapi import FastAPI
from app.routers import router  
from app.logger_config import logger

app = FastAPI()

# Include the router with an optional prefix
app.include_router(router, prefix="/app")



if __name__ == "__main__":
    import uvicorn
    logger.info("Starting App.....")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)