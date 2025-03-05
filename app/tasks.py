from celery import Celery
from bs4 import BeautifulSoup
import requests
from app.models import seo_analysis_collection  # Import MongoDB collection
from app.seo_rules import evaluate_seo_rules
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)

# Initialize logger
logger = logging.getLogger(__name__)

# Initialize Celery
celery_app = Celery("tasks", broker="redis://localhost:6379/0")  # Update for local Redis
celery_app.conf.broker_connection_retry_on_startup = True
celery_app.conf.worker_pool = "solo"

@celery_app.task
def perform_seo_analysis(scan_id: str, url: str):
    try:
        # Fetch the scan object
        scan = seo_analysis_collection.find_one({"_id": scan_id})
        if not scan:
            logger.error(f"Scan with ID {scan_id} not found.")
            return

        logger.info(f"Starting SEO analysis for scan ID {scan_id}, URL: {url}")

        # Update status to "in_progress"
        seo_analysis_collection.update_one({"_id": scan_id}, {"$set": {"status": "in_progress"}})
        logger.info(f"Updated status to 'in_progress' for scan ID {scan_id}")

        try:
            # Fetch the page content with a timeout
            response = requests.get(url, timeout=10)
            soup = BeautifulSoup(response.content, "lxml")

            # Evaluate SEO rules
            results = evaluate_seo_rules(soup, url)

            # Update result and status
            seo_analysis_collection.update_one(
                {"_id": scan_id},
                {"$set": {"status": "completed", "result": results}}
            )
            logger.info(f"SEO analysis completed for scan ID {scan_id}")
        except Exception as e:
            logger.error(f"Error during SEO analysis for scan ID {scan_id}: {str(e)}")
            seo_analysis_collection.update_one(
                {"_id": scan_id},
                {"$set": {"status": "failed", "result": {"error": str(e)}}}
            )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")