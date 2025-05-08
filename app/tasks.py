# app/tasks.py
from celery import Celery
from bs4 import BeautifulSoup
import requests
from app.seo_rules import evaluate_seo_rules
from app.logger_config import logger

# Import repository functions
from app.seo_repository import get_seo_scan_by_id, update_seo_scan_status, update_seo_scan_result

# Initialize Celery
celery_app = Celery("tasks", broker="redis://localhost:6379/0")
celery_app.conf.broker_connection_retry_on_startup = True
celery_app.conf.worker_pool = "solo"

@celery_app.task
def perform_seo_analysis(scan_id: str, base_url: str):
    try:
        logger.info(f"Received SEO analysis request for URL: {base_url} with scan_id {scan_id}")

        # Fetch the scan object from MongoDB
        scan = get_seo_scan_by_id(scan_id)
        if not scan:
            logger.error(f"Scan with ID {scan_id} not found.")
            return

        # Update status to "in_progress"
        update_seo_scan_status(scan_id, "in_progress")
        logger.info(f"Updated status to 'in_progress' for scan ID {scan_id}")

        # Perform SEO analysis
        try:
            logger.info(f"Fetching page content for URL: {base_url}")
            response = requests.get(base_url, timeout=10)
            response.raise_for_status()
            logger.info(f"Parsing HTML content with BeautifulSoup...")
            soup = BeautifulSoup(response.content, "lxml")

            results = evaluate_seo_rules(soup, base_url)
            logger.info(f"SEO analysis completed for scan ID {scan_id}. Results: {results}")

            # Save result and update status
            update_seo_scan_status(scan_id, "completed")
            update_seo_scan_result(scan_id, results)

        except Exception as e:
            logger.error(f"Error during SEO analysis for scan ID {scan_id}: {e}")
            update_seo_scan_status(scan_id, "failed")
            update_seo_scan_result(scan_id, {"error": str(e)})

    except Exception as e:
        logger.error(f"Unexpected error in task for scan ID {scan_id}: {e}")