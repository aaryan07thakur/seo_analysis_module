# app/service.py
import uuid
from urllib.parse import urlparse
import requests
from typing import Optional, Dict

from app.seo_repository import (
    create_seo_scan,
    get_seo_scan_by_id
)
from app.tasks import perform_seo_analysis
from app.logger_config import logger


class SEOService:
    def __init__(self):
        pass

    def validate_and_get_base_url(self, url: str) -> Optional[str]:
        logger.info(f"Starting validate_and_get_base_url function")
        """
        Validates URL format and extracts the base URL.
        - Adds 'https://' protocol if missing
        - Handles domains like .com, .org, .net, .edu, country-specific TLDs, etc.
        - Supports various protocols (http, https, ftp, etc.)
        - Returns None if URL format is invalid
        - Does not perform DNS lookup to verify if domain exists
        """
        url = url.strip()

        # Add scheme if missing
        if not url.startswith(('http://', 'https://', 'ftp://', 'sftp://')):
            url = f"https://{url}"
            logger.debug(f"URL missing protocol, prepended 'https://'. Updated URL: {url}")

        # Parse the URL to validate its structure
        try:
            parsed_url = urlparse(url)
            logger.info(f"Parsed URL: {parsed_url}")

            # Check if scheme and netloc are present
            if not all([parsed_url.scheme, parsed_url.netloc]):
                logger.error(f"Invalid URL format (missing scheme or netloc): {url}")
                return None

            # Basic domain format validation using regex
            import re
            domain_pattern = re.compile(
                r'^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z0-9][a-zA-Z0-9\-]{0,61}[a-zA-Z0-9]$'
            )

            if not domain_pattern.match(parsed_url.netloc.split(':')[0]):  # Remove port if present
                logger.error(f"Invalid domain format: {parsed_url.netloc}")
                return None

            # Construct the base URL
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            logger.info(f"Extracted base URL: {base_url}")
            return base_url

        except Exception as e:
            logger.error(f"URL validation error for {url}: {str(e)}")
            return None

    def check_base_url_reachability(self, base_url: str) -> dict:
        """
        Checks if the base URL is reachable by making an HTTP HEAD request.
        Handles URLs starting with 'www.' by prepending 'https://'.
        Returns a dictionary with the result of the check.
        """
        logger.info(f"Starting check_base_url_reachability")
        try:
            # Normalize the URL
            parsed_url = urlparse(base_url)
            logger.info(f"Parsed URL: {parsed_url}")
            if not parsed_url.scheme:  # No scheme (e.g., starts with 'www.')
                base_url = f"https://{base_url}"  # Prepend 'https://'

            # Make an HTTP HEAD request to check reachability
            head_response = requests.head(base_url, timeout=5)
            if head_response.status_code >= 400:
                return {
                    "url": base_url,
                    "reachable": False,
                    "status_code": head_response.status_code,
                    "reason": f"Base URL is unreachable. Status code: {head_response.status_code}"
                }
            else:
                return {
                    "url": base_url,
                    "reachable": True,
                    "status_code": head_response.status_code,
                    "reason": f"Base URL is reachable. Status code: {head_response.status_code}"
                }
        except requests.RequestException as e:
            return {
                "url": base_url,
                "reachable": False,
                "status_code": None,
                "reason": f"Failed to reach base URL: {str(e)}"
            }

    def start_seo_analysis(self, url: str):
        scan_id = str(uuid.uuid4())
        logger.info(f"Validating URL: {url}")

        base_url = self.validate_and_get_base_url(url)
        if not base_url:
            logger.warning(f"Invalid URL format: {url}")
            raise ValueError("Invalid URL format")

        logger.info(f"Checking reachability of base URL: {base_url}")
        reachability = self.check_base_url_reachability(base_url)

        if not reachability["reachable"]:
            logger.warning(f"Base URL unreachable: {reachability['reason']}")
            scan_data = {
                "_id": scan_id,
                "url": base_url,
                "status": "failed",
                "result": {"error": reachability["reason"]}
            }

            # # Save failed scan in DB
            # create_seo_scan(scan_id=scan_id, url=url)
            # update_seo_scan_status(scan_id, "failed")
            # update_seo_scan_result(scan_id, {"error": reachability["reason"]})
            return scan_data

        try:
            scan = create_seo_scan(scan_id=scan_id, url=base_url)
            logger.info(f"Scan object inserted with ID: {scan}")
        except Exception as e:
            logger.error(f"Error inserting scan object: {e}")
            raise

        perform_seo_analysis.delay(scan_id, base_url)

        return scan

    def get_seo_analysis(self, scan_id: str):
        logger.info(f"Fetching SEO analysis data for scan ID: {scan_id}")
        scan = get_seo_scan_by_id(scan_id)
        if not scan:
            logger.warning(f"Scan with ID {scan_id} not found")
            raise Exception("Scan not found")
        return scan