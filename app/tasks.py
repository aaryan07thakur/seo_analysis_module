from celery import Celery
from bs4 import BeautifulSoup
import requests
from app.models import seo_analysis_collection
from app.seo_rules import evaluate_seo_rules
from app.logger_config import logger  # Import logger for Celery

# Initialize Celery
celery_app = Celery("tasks", broker="redis://localhost:6379/0")
celery_app.conf.broker_connection_retry_on_startup = True
celery_app.conf.worker_pool = "solo"  # Set worker pool to solo for easier debugging

@celery_app.task
def perform_seo_analysis(scan_id: str, url: str):
    try:
        logger.info(f"Received SEO analysis request for URL: {url} with scan_id {scan_id}")

        # Fetch the scan object from MongoDB
        scan = seo_analysis_collection.find_one({"_id": scan_id})
        if not scan:
            logger.error(f"Scan with ID {scan_id} not found.")
            return

        # Update status to "in_progress"
        seo_analysis_collection.update_one({"_id": scan_id}, {"$set": {"status": "in_progress"}})
        logger.info(f"Updated status to 'in_progress' for scan ID {scan_id}")

        # Perform SEO analysis
        try:
            logger.info(f"Fetching page content for URL: {url}")
            response = requests.get(url, timeout=10)       #Sends an HTTP request to fetch the webpage content
            response.raise_for_status()  # Raise HTTPError for bad responses
            soup = BeautifulSoup(response.content, "lxml")

            results = evaluate_seo_rules(soup, url)      #Calls the evaluate_seo_rules() function to analyze the page based on SEO rules.
            logger.info(f"SEO analysis completed for scan ID {scan_id}. Results: {results}")    #stores the Results in results

            # Update result and status in MongoDB
            seo_analysis_collection.update_one(
                {"_id": scan_id},
                {"$set": {"status": "completed", "result": results}}
            )
        except Exception as e:
            logger.error(f"Error during SEO analysis for scan ID {scan_id}: {e}")
            seo_analysis_collection.update_one(
                {"_id": scan_id},
                {"$set": {"status": "failed", "result": {"error": str(e)}}}
            )
            return
    except Exception as e:
        logger.error(f"Unexpected error in task for scan ID {scan_id}: {e}")
