import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
from itertools import islice
from collections import defaultdict
from datetime import datetime
from collections import Counter 
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from hashlib import md5
import asyncio
import aiohttp
from dateutil import parser
from functools import wraps
from aiohttp import ClientTimeout
from app.logger_config import logger
from typing import Dict, Any, List,Optional
import ssl
import socket
import json
import gzip
import io


def measure_execution_time(func):
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
        finally:
            end_time = time.time()
            execution_time = round(end_time - start_time, 4)
            print(f"{func.__name__} executed in {execution_time} seconds")
        return result

    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
        finally:
            end_time = time.time()
            execution_time = round(end_time - start_time, 4)
            print(f"{func.__name__} executed in {execution_time} seconds")
        return result
    return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper



# Meta Tags Evaluation
@measure_execution_time
def check_meta_tags(soup: BeautifulSoup, results: dict) -> None:
    logger.info(" start Checking meta tags...")
    """
    Analyzes the title and meta description tags of a parsed HTML and updates
    the 'results' dictionary with details about their presence and length.

    Args:
        soup: A BeautifulSoup object representing the parsed HTML.
        results: A dictionary to store the analysis results. It is expected to
                have a structure where results["results"]["meta_tags"] is a
                dictionary to which the analysis outcomes will be added.
    """
    meta_tags_results = {}

    # Analyze title tag
    title_tag = soup.title
    title_exists = title_tag is not None
    
    if title_exists and title_tag.string and title_tag.string.strip():
        title_text = title_tag.string.strip()
        title_value = title_text
        title_status = "Good"
        title_rating = 10
        title_reason = "Title tag present with content"
    elif title_exists:
        title_text = ""
        title_value = "Null"
        title_status = "Poor"
        title_rating = 0
        title_reason = "Title tag exists but is empty. Consider adding Titles-critical for SEO."
    else:
        title_text = ""
        title_value = False
        title_status = "Poor"
        title_rating = 0
        title_reason = "Missing title tag - critical for SEO"
    
    title_len = len(title_text)

    meta_tags_results["title_tag_exists"] = {
        "value": title_value,
        "status": title_status,
        "rating": title_rating,
        "reason": title_reason,
        "category":"High Priority",
    }

    title_length_optimal = 50 <= title_len <= 60
    meta_tags_results["title_tag_length"] = {
        "value": title_len,
        "status": "Good" if title_length_optimal else "Needs Improvement",
        "rating": 10 if title_length_optimal else 5,
        "reason": "Optimal length (50-60 chars)" if title_length_optimal else 
                f"Title length: {title_len} chars (should be 50-60)",
        "category":"High Priority",
    }

    # Analyze meta description tag
    meta_description = soup.find("meta", attrs={"name": "description"})
    meta_desc_exists = meta_description is not None
    
    if meta_desc_exists and meta_description.get("content") and meta_description.get("content").strip():
        desc_content = meta_description.get("content").strip()
        # Only use the content text, not the entire HTML tag
        meta_desc_value = desc_content
        meta_desc_status = "Good"
        meta_desc_rating = 10
        meta_desc_reason = "Meta description present with content"
    elif meta_desc_exists:
        desc_content = ""
        meta_desc_value = False
        meta_desc_status = "Poor"
        meta_desc_rating = 1
        meta_desc_reason = "Meta description exists but is empty"
    else:
        desc_content = ""
        meta_desc_value = False
        meta_desc_status = "Poor"
        meta_desc_rating = 1
        meta_desc_reason = "Missing meta description"
    
    meta_tags_results["meta_description_exists"] = {
        "value": meta_desc_value,
        "status": meta_desc_status,
        "rating": meta_desc_rating,
        "reason": meta_desc_reason,
        "category":"High Priority",
    }

    desc_length_optimal = 150 <= len(desc_content) <= 160
    meta_tags_results["meta_description_length"] = {
        "value": len(desc_content),
        "status": "Good" if desc_length_optimal else "Needs Improvement",
        "rating": 10 if desc_length_optimal else 6,
        "reason": "Optimal length (150-160 chars)" if desc_length_optimal else 
                f"Length: {len(desc_content)} chars (should be 150-160)",
        "category":"High Priority",
    }
    
    results["results"]["meta_tags"] = meta_tags_results
    logger.info("Meta tags check completed.")



@measure_execution_time
def check_meta_keywords_tag(soup, results):
    """
    Analyzes the presence of meta keywords tag for SEO recommendations.
    
    Modern SEO best practices consider meta keywords unnecessary and potentially harmful.
    This check flags the presence of this tag as non-optimal while explaining the rationale.
    """
    # Use correct case for HTML attribute and simplify check
    meta_keywords = soup.find("meta", attrs={"name": "keywords"})
    keywords_found = meta_keywords is not None
    # Use clearer status indicators and explanations
    status = "poor" if keywords_found else "Good"
    rating = 2 if keywords_found else 10
    reason = (
        "Meta keywords tag found - considered unnecessary in modern SEO "
        "and can be removed"
        if keywords_found 
        else "No meta keywords tag found - follows modern SEO best practices"
    )
    
    # Add content preview if tag exists
    content_preview = (
        meta_keywords.get("content", "")[:50] + "..."
        if keywords_found 
        else "None"
    )
    results["results"]["meta_tags"]["meta_keywords_exists"] = {
        "value": f"Content: {content_preview}" if keywords_found else keywords_found,
        "status": status,
        "rating": rating,
        "reason": reason,
        "category":"Low Priority",
    }


# # Headings Evaluation
@measure_execution_time
def check_headings(soup: BeautifulSoup, results: Dict[str, Any]) -> None:
    """
    Analyzes headings (h1-h6) in the HTML to determine their presence, count, and uniqueness,
    providing relevant metrics and ratings in the results dictionary.
    """
    # Single pass collection
    all_headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
    heading_counts = defaultdict(list)
    for h in all_headings:
        heading_counts[h.name].append(h)

    # Check missing status once
    missing = {
        'h1': not heading_counts.get('h1'),
        'h2': not heading_counts.get('h2'),
        'h3': not heading_counts.get('h3')
    }

    # Pre-calculate ratings
    RATING_RULES = {
        'h1': (10, 1),
        'h2': (8, 2),
        'h3': (6, 4),
        'h4': (5, 5),
        'h5': (5, 5),
        'h6': (4, 4)
    }

    headings_results = {}
    
    for level in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
        tags = heading_counts.get(level, [])
        count = len(tags)
        exists = count > 0
        
        # Calculate rating
        base_rating, missing_rating = RATING_RULES[level]
        rating = base_rating if exists else missing_rating
        
        # Special h4 case
        if level == 'h4' and exists and all(missing.values()):
            rating = 4

        # Build exists entry
        headings_results[f"{level}_tag_exists"] = {
            "value": count,
            "status": "Good" if exists else "Poor" if level == 'h1' else "Needs Improvement",
            "rating": rating,
            "reason": f"{count} {level.upper()} tag{'s' if count !=1 else ''} found" if exists 
                    else f"No {level.upper()} tags found" + (" - critical" if level in ['h1','h2'] else ""),
            "category":"High Priority",
        }

        # Handle h1 uniqueness
        if level == 'h1':
            unique = count == 1
            headings_results["h1_tag_unique"] = {
                "value": unique,
                "status": "Good" if unique else "Poor",
                "rating": 10 if unique else (0 if count == 0 else 4),  # 0 for no H1, 4 for multiple H1s but not unique
                "reason": "Single H1" if unique else f"{count} H1s found" if count > 0 else "No H1 tags found-Important for SEO",
                "category":"High Priority",
            }

    results["results"]["headings"] = headings_results


# # Content Evaluation
@measure_execution_time
def check_content(soup: BeautifulSoup, results: Dict[str, Any]) -> None:
    """
    Analyzes webpage content for essential SEO factors including image alt attributes,
    content length, and alt text quality.
    
    """
    content_results = {}
    
    # Image analysis - with optimized collection
    images = soup.find_all('img')
    alt_data = [
        (bool(img.get('alt') and img['alt'].strip() != ''),  # Check for non-empty alt
        len((img.get('alt') or '').strip().split()))  # Word count of alt text
        for img in images
    ]
    
    # Alt attribute existence check
    if images:
        all_alts_present = all(has_alt for has_alt, _ in alt_data)
        missing_count = sum(not has_alt for has_alt, _ in alt_data)
        
        content_results["alt_attributes_exist"] = {
            "value": all_alts_present,
            "status": "Good" if all_alts_present else "Needs Improvement",
            "rating": 9 if all_alts_present else max(1, 9 - missing_count),
            "reason": (
                "All images have alt attributes" if all_alts_present 
                else f"{missing_count} images missing alt text"
            ),
            "category":"High Priority",
        }
        
        # Alt text quality check (only for images with alt text)
        imgs_with_alt = [(has_alt, word_count) for has_alt, word_count in alt_data if has_alt]
        if imgs_with_alt:
            all_descriptive = all(word_count > 3 for _, word_count in imgs_with_alt)
            poor_alts = sum(0 < word_count <= 3 for _, word_count in imgs_with_alt)
            
            content_results["alt_attributes_descriptive"] = {
                "value": all_descriptive,
                "status": "Good" if all_descriptive else "Needs Improvement",
                "rating": 8 if all_descriptive else max(3, 8 - poor_alts),
                "reason": (
                    "All alt texts are descriptive" if all_descriptive
                    else f"{poor_alts} alt texts need improvement (aim for 4+ words)"
                ),
                "category":"High Priority"
            }
        else:
            content_results["alt_attributes_descriptive"] = {
                "value": False,
                "status": "Not Applicable",
                "rating": 5,
                "reason": "Cannot check descriptiveness due to missing alt attributes",
                "category":"High Priority",
            }
    else:
        # No images case
        content_results["alt_attributes_exist"] = {
            "value": True,
            "status": "Not Applicable",
            "rating": 10,
            "reason": "No images found on the page",
            "category":"High Priority",
        }
        
        content_results["alt_attributes_descriptive"] = {
            "value": True,
            "status": "Not Applicable",
            "rating": 10,
            "reason": "No images found to check alt text descriptiveness",
            "category":"High Priority",
        }
    
    # Content length analysis - more efficient text extraction
    main_text = ' '.join(soup.stripped_strings)
    word_count = len(main_text.split())
    
    content_rating = 10 if word_count >= 1000 else 8 if word_count >= 500 else 5
    content_results["content_length"] = {
        "value": word_count,
        "status": "Good" if word_count >= 500 else "Needs Improvement",
        "rating": content_rating,
        "reason": (
            f"Optimal content length ({word_count} words)" if word_count >= 1000
            else f"Good content length ({word_count} words)" if word_count >= 500
            else f"Short content ({word_count} words) - aim for 500+ words for Good SEO"
        ),
        "category":"High Priority",
    }
    # Add to results
    results["results"]["content"] = content_results


# Technical SEO
@measure_execution_time
async def check_technical(soup: BeautifulSoup, results: Dict[str, Any], base_url: str) -> None:
    """
    Analyzes technical SEO aspects including canonical tags and robots.txt.
    Handles all canonical tag validation in one place.
    """
    technical_section = results["results"].setdefault("technical", {})
    
    # Consolidated canonical tag validation
    canonical_tag = soup.find("link", rel="canonical")
    parsed_base_url = urlparse(base_url)
    
    canonical_data = {
        "exists": False,
        "self_referencing": False,
        "status": "Needs Improvement",
        "rating": 3,
        "reason": "Missing canonical tag",
        "category":"High Priority",
    }

    if canonical_tag and (href := canonical_tag.get("href")):
        try:
            # Normalize URLs for accurate comparison
            canonical_url = urljoin(base_url, href)
            parsed_canonical = urlparse(canonical_url)
            
            # Strip query params and fragments from both URLs
            base_path = parsed_base_url._replace(query="", fragment="").geturl()
            canonical_path = parsed_canonical._replace(query="", fragment="").geturl()
            
            canonical_data.update({
                "exists": True,
                "self_referencing": canonical_path.rstrip('/') == base_path.rstrip('/'),
                "reason": f"Canonical URL: {canonical_path}"
            })
        except Exception as e:
            canonical_data["reason"] = f"Invalid canonical URL: {str(e)}"
    
    # Set final status and rating
    if canonical_data["self_referencing"]:
        canonical_data.update({
            "status": "Good",
            "rating": 9,
            "reason": "Proper self-referencing canonical",
            "category":"High Priority",
        })
    elif canonical_data["exists"]:
        canonical_data.update({
            "status": "Needs Improvement", 
            "rating": 5,
            "reason": "Canonical points to different URL",
            "category":"High Priority",
        })
    
    technical_section["canonical_tag"] = canonical_data
    
    # Robots.txt check remains the same
    robots_url = urljoin(base_url, "/robots.txt")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(robots_url, timeout=ClientTimeout(total=2)) as response:
                technical_section["robots_txt"] = {
                    "value": response.status == 200,
                    "status": "Good" if response.status == 200 else "Needs Improvement",
                    "rating": 8 if response.status == 200 else 5,
                    "reason": "robots.txt found" if response.status == 200 else f"robots.txt not found (status: {response.status})",
                    "status_code": response.status,
                    "category":"High Priority",
                }
    except Exception as e:
        technical_section["robots_txt"] = {
            "value": False,
            "status": "Error",
            "rating": 1,
            "reason": f"robots.txt check failed: {type(e).__name__}",
            "status_code": 0,
            "category":"High Priority",
        }

# # Security
@measure_execution_time
async def check_security(soup: BeautifulSoup, results: Dict[str, Any], base_url: str) -> None:
    """
    Analyzes website security features including SSL/TLS configuration.
    Checks:
    1. HTTPS implementation
    2. SSL certificate validity
    3. Security headers presence
    """
    security_data = {
        "ssl_installed": False,
        "cert_valid": False,
        "cert_expiry_days": 0,
        "security_headers": [],
        "reason": ""
    }

    # Initialize security_headers as an empty dictionary
    security_headers = {}

    # Parse URL to check if HTTPS is being used
    parsed_url = urlparse(base_url)
    security_data["ssl_installed"] = parsed_url.scheme == 'https'
    hostname = parsed_url.hostname
    
    # Only check certificate if HTTPS is enabled
    if security_data["ssl_installed"]:
        try:
            # Use asyncio to run the blocking SSL check in a thread pool
            cert_data = await asyncio.to_thread(check_ssl_certificate, hostname)
            security_data.update(cert_data)
        except Exception as e:
            security_data["reason"] = f"Certificate check failed: {type(e).__name__}"


            # Initialize security_headers before the try block
    security_headers = {
        'strict-transport-security': 'HSTS',
        'content-security-policy': 'CSP',
        'x-frame-options': 'X-Frame-Options',
        'x-content-type-options': 'X-Content-Type',
        'referrer-policy': 'Referrer-Policy',
        'permissions-policy': 'Permissions-Policy',
        'x-xss-protection': 'XSS-Protection'
    }
    
    # Check security headers with proper SSL verification
    try:
        async with aiohttp.ClientSession() as session:
            # Only disable SSL verification if we're debugging or testing
            # For production, always verify SSL
            async with session.get(
                base_url, 
                timeout=ClientTimeout(total=10),
                ssl=None  # Use default SSL verification
            ) as response:
                found_headers = []
                for header_name, header_label in security_headers.items():
                    if header_name in [h.lower() for h in response.headers]:
                        found_headers.append(header_label)
                
                security_data["security_headers"] = found_headers
                
    except Exception as e:
        security_data["security_headers"] = []
        security_data["headers_error"] = f"Header check failed: {type(e).__name__}"

    # Build final results with better ratings and descriptions
    security_results = {}
    # HTTPS evaluation
    security_results["ssl_installed"] = {
        "value": security_data["ssl_installed"],
        "status": "Good" if security_data["ssl_installed"] else "Critical",
        "rating": 10 if security_data["ssl_installed"] else 1,
        "reason": "HTTPS enabled" if security_data["ssl_installed"] else "No HTTPS - serious security risk",
        "category":"High Priority",
    }
    
    # Certificate health evaluation
    if security_data["ssl_installed"]:
        days_remaining = security_data.get("cert_expiry_days", 0)
        is_valid = security_data.get("cert_valid", False)
        
        # More nuanced certificate rating based on expiration time
        cert_rating = 10  # Default for valid cert with plenty of time
        cert_status = "Good"
        cert_reason = f"Valid certificate ({days_remaining} days remaining)"
        
        if not is_valid:
            cert_rating = 1
            cert_status = "Critical"
            cert_reason = "Invalid certificate"
        elif days_remaining < 7:
            cert_rating = 3
            cert_status = "Critical"
            cert_reason = f"Certificate expiring very soon ({days_remaining} days remaining)"
        elif days_remaining < 30:
            cert_rating = 5
            cert_status = "Warning"
            cert_reason = f"Certificate expiring soon ({days_remaining} days remaining)"
            
        security_results["certificate_health"] = {
            "value": is_valid,
            "status": cert_status,
            "rating": cert_rating,
            "reason": cert_reason,
            "days_remaining": days_remaining,
            "category":"High Priority",
        }
    else:
        security_results["certificate_health"] = {
            "value": False,
            "status": "Not Applicable",
            "rating": 0,
            "reason": "Cannot check certificate - site not using HTTPS",
            "days_remaining": 0,
            "category":"High Priority",
        }
    
    # Security headers evaluation with better scoring
    header_count = len(security_data["security_headers"])
    max_headers = len(security_headers)
    header_percentage = (header_count / max_headers) * 100 if max_headers > 0 else 0
    
    if header_count == 0:
        header_status = "Critical"
        header_rating = 1
        header_reason = "No security headers found"
    elif header_percentage < 30:
        header_status = "Poor"
        header_rating = 3
        header_reason = f"Few security headers ({header_count}/{max_headers})"
    elif header_percentage < 60:
        header_status = "Needs Improvement"
        header_rating = 5
        header_reason = f"Some security headers ({header_count}/{max_headers})"
    elif header_percentage < 85:
        header_status = "Good"
        header_rating = 8
        header_reason = f"Most security headers present ({header_count}/{max_headers})"
    else:
        header_status = "Excellent"
        header_rating = 10
        header_reason = f"All important security headers present ({header_count}/{max_headers})"
    
    if security_data["security_headers"]:
        header_reason += f": {', '.join(security_data['security_headers'])}"
    elif "headers_error" in security_data:
        header_reason = security_data["headers_error"]
    
    security_results["security_headers"] = {
        "value": header_count,
        "status": header_status,
        "rating": header_rating,
        "reason": header_reason,
        "found_headers": security_data["security_headers"],
        "total_possible": max_headers,
        "category":"High Priority",
    }
    # Add the results to the main results dictionary
    results["results"]["security"] = security_results



@measure_execution_time
def check_ssl_certificate(hostname):
    """
    Check SSL certificate validity and expiration (runs in a thread pool).
    This is a blocking function that should be called with asyncio.to_thread.
    
    Args:
        hostname: The hostname to check
        
    Returns:
        Dict containing certificate validity and expiration information
    """
    cert_data = {
        "cert_valid": False,
        "cert_expiry_days": 0
    }
    
    try:
        context = ssl.create_default_context()
        logger.info(f"Checking SSL certificate for {hostname}")

        with socket.create_connection((hostname, 443), timeout=5) as sock:
            logger.info(f"Connected to {hostname} on port 443")
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                logger.info(f"SSL connection established completed for {hostname}")
                cert = ssock.getpeercert()
                logger.info(f"Certificate details: {cert}")
                # Certificate expiration check
                expiry_date = datetime.utcnow().strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
                remaining_days = (expiry_date - datetime.utcnow()).days
                
                cert_data.update({
                    "cert_valid": remaining_days > 0,
                    "cert_expiry_days": remaining_days,
                    "issuer": dict(x[0] for x in cert['issuer'])
                })
    except Exception as e:
        cert_data["reason"] = f"Certificate check failed: {type(e).__name__}"
        
    return cert_data



# # URL Structure
@measure_execution_time
def check_url(soup: BeautifulSoup, results: Dict[str, Any], base_url: str, target_keyword: Optional[str] = None) -> None:
    """
    Analyzes the URL for SEO-related factors, including length and keyword presence.

    Args:
        soup: A BeautifulSoup object (although not directly used in this function).
        results: A dictionary to store the analysis results. It is expected to
                have a structure where results["results"]["url"] is a
                dictionary to which the analysis outcomes will be added.
        url: The URL of the webpage being analyzed.
        target_keyword: An optional target keyword to check for in the URL path.
    """
    base_url_results = {}
    # parsed_url = urlparse(base_url)
    base_len = len(base_url)

    # Check URL Length
    base_url_results["url_length_optimized"] = {
        "value": base_len <= 75,
        "status": "Good" if base_len <= 75 else "Needs Improvement",
        "rating": 9 if base_len <= 75 else 5,
        "reason": f"URL length: {base_len} characters" if base_len <= 75 else "URL is too long (should be <= 75 characters)",
        "category":"Average Priority",
    }

    # Check Keyword in URL
    keyword_in_base_url = False
    if target_keyword:
        keyword_in_base_url = target_keyword.lower() in base_url.lower()

    base_url_results["base_url_keywords"] = {
        "value": keyword_in_base_url,
        "status": "Good" if keyword_in_base_url else "Needs Improvement",
        "rating": 10 if keyword_in_base_url else 5,
        "reason": f"Target keyword '{target_keyword}' found in URL" if keyword_in_base_url and target_keyword else (
            f"Target keyword '{target_keyword}' missing from URL" if target_keyword else "No target keyword specified to check in URL"
        ),
        "category":"High Priority",
    }

    results["results"]["url"] = base_url_results



# # Mobile Optimization
@measure_execution_time
def check_mobile(soup: BeautifulSoup, results: dict) -> None:
    """
    Analyzes mobile responsiveness and viewport configuration.
    Checks:
    1. Presence of viewport meta tag
    2. Viewport content validity
    3. Mobile-friendly HTML features
    Args:
        soup: Parsed HTML document
        results: Dictionary to store analysis results
    """
    viewport = soup.find("meta", attrs={"name": "viewport"})
    content = viewport.get("content", "").lower() if viewport else ""
    
    # Viewport content validation
    valid_components = {
        "width=device-width": False,
        "initial-scale=1": False,
        "user-scalable=yes": True,  # Default acceptable if not specified
        "maximum-scale=5": True ,     # Allow reasonable zoom
        "category":"High Priority",
    }
    
    if content:
        for component in content.split(","):
            key_value = component.strip().split("=")
            if len(key_value) == 2:
                key = key_value[0].strip()
                value = key_value[1].strip()
                if key == "width" and value != "device-width":
                    valid_components["width=device-width"] = False
                elif key == "initial-scale" and value != "1":
                    valid_components["initial-scale=1"] = False
                elif key == "user-scalable" and value == "no":
                    valid_components["user-scalable=yes"] = False
                elif key == "maximum-scale" and float(value) < 2:
                    valid_components["maximum-scale=5"] = False

    # Calculate viewport quality score
    viewport_score = sum(1 for valid in valid_components.values() if valid)
    total_checks = len(valid_components)
    
    results["results"]["mobile"]["viewport_analysis"] = {
        "exists": bool(viewport),
        "content_valid": viewport_score == total_checks,
        "content_value": content,
        "status": (
            "Good" if viewport_score == total_checks else
            "Needs Improvement" if viewport else 
            "Poor"
        ),
        "rating": (
            10 if viewport_score == total_checks else
            6 if viewport else
            3
        ),
        "reason": (
            "Proper viewport configuration" if viewport_score == total_checks else
            f"Partial configuration: {content}" if viewport else
            "Missing viewport meta tag - critical for mobile"
        ),
        "checks": {
            "device_width": valid_components["width=device-width"],
            "proper_scale": valid_components["initial-scale=1"],
            "zoom_allowed": valid_components["user-scalable=yes"],
            "max_zoom": valid_components["maximum-scale=5"]
        },
        "category":"High Priority",
    }

# # Schema Markup
@measure_execution_time
def check_schema(soup: BeautifulSoup, results: Dict[str, Any]) -> None:
    """
    Checks for the presence of schema.org markup (JSON-LD) in the HTML.
    It also attempts to parse the schema to identify potential issues.

    Args:
        soup: A BeautifulSoup object representing the parsed HTML.
        results: A dictionary to store the analysis results. It is expected to
                have a structure where results["results"]["schema"] is a
                dictionary to which the analysis outcomes will be added.
    """
    schema_tags = soup.find_all("script", type="application/ld+json")
    schema_results = {}
    schema_exists = len(schema_tags) > 0

    schema_results["schema_markup_exists"] = {
        "value": schema_exists,
        "status": "Good" if schema_exists else "Needs Improvement",
        "rating": 8 if schema_exists else 5,
        "reason": f"{len(schema_tags)} schema (JSON-LD) tags found" if schema_exists else "No schema.org markup (JSON-LD) found - consider adding for better SEO",
        "category":"Average Priority",
    }

    if schema_exists:
        valid_schema = True
        error_messages = []
        for tag in schema_tags:
            try:
                json.loads(tag.string)
            except json.JSONDecodeError as e:
                valid_schema = False
                error_messages.append(f"Invalid JSON in schema tag: {e}")

        schema_results["schema_markup_valid"] = {
            "value": valid_schema,
            "status": "Good" if valid_schema else "Needs Improvement",
            "rating": 10 if valid_schema else 6,
            "reason": "Schema markup is valid JSON" if valid_schema else "One or more schema markup blocks contain invalid JSON",
            "errors": error_messages if error_messages else None,
            "category":"Average Priority",
        }
    else:
        schema_results["schema_markup_valid"] = {
            "value": False,
            "status": "Not Applicable",
            "rating": 1,
            "reason": "No schema markup found to validate",
            "category":"Average Priority",
        }

    results["results"]["schema"] = schema_results

# # Link Analysis
def check_links(soup: BeautifulSoup, results: Dict[str, Any], base_url: str) -> None:
    """
    Analyzes internal and external links on the webpage for SEO relevance.

    Checks:
    - Presence of internal links.
    - Presence of external links.
    - Attempts to identify and report potential issues with internal links
    (e.g., broken links - basic check, more robust checking would require
    HTTP requests).

    Args:
        soup: A BeautifulSoup object representing the parsed HTML.
        results: A dictionary to store the analysis results. It is expected to
                have a structure where results["results"]["links"] is a
                dictionary to which the analysis outcomes will be added.
        url: The URL of the webpage being analyzed, used for context when
            determining internal vs. external links.
    """
    links = soup.find_all("a", href=True)
    parsed_base_url = urlparse(base_url)
    internal_links: List[BeautifulSoup] = []
    external_links: List[BeautifulSoup] = []

    for link in links:
        href = link.get("href").strip()
        if href and not href.startswith("#"):  # Ignore fragment identifiers
            parsed_href = urlparse(href)
            if not parsed_href.netloc or parsed_href.netloc == parsed_base_url.netloc:
                internal_links.append(link)
            else:
                external_links.append(link)

    links_results = {}

    # Internal Links
    internal_exists = len(internal_links) > 0
    links_results["internal_links_exist"] = {
        "value": internal_exists,
        "status": "Good" if internal_exists else "Needs Improvement",
        "rating": 9 if internal_exists else 5,
        "reason": f"{len(internal_links)} internal links found" if internal_exists else "No internal links found - important for site navigation",
        "category":"High Priority",

    }

    # External Links
    external_exists = len(external_links) > 0
    links_results["external_links_exist"] = {
        "value": external_exists,
        "status": "Good" if external_exists else "Needs Improvement",
        "rating": 7 if external_exists else 5,
        "reason": f"{len(external_links)} external links found" if external_exists else "No external links found",
        "category":"High Priority",
    }

    results["results"]["links"] = links_results



@measure_execution_time
def check_canonical_tag_valid(soup: BeautifulSoup, results: dict, base_url: str) -> None:
    # Ensure "technical" section exists
    if "technical" not in results["results"]:
        results["results"]["technical"] = {}
        logger.info("Created 'technical' section in results")
    
    # Ensure "canonical_tag" subkey exists
    if "canonical_tag" not in results["results"]["technical"]:
        results["results"]["technical"]["canonical_tag"] = {}

    # Deep validation logic
    canonical_tag = soup.find("link", rel="canonical")
    current_url = base_url.split("?")[0].split("#")[0]
    
    if canonical_tag and (href := canonical_tag.get("href")):
        canonical_url = urljoin(base_url, href).split("?")[0].split("#")[0]
        is_valid = (canonical_url == current_url)
        
        # Update existing canonical_tag entry
        results["results"]["technical"]["canonical_tag"].update({
            "self_referencing": is_valid,
            "status": "Good" if is_valid else "Needs Improvement",
            "rating": 9 if is_valid else 5,
            "reason": f"Canonical URL {'matches' if is_valid else 'differs'} ({canonical_url})"
        })
    else:
        results["results"]["technical"]["canonical_tag"].update({
            "reason": "No canonical tag found" if not canonical_tag else "Invalid href"
        })



@measure_execution_time
def check_robots_meta_tag_exists(soup, results):
    robots_meta = soup.find("meta", attrs={"name": "robots"})
    robots_meta_value =  robots_meta["content"] if robots_meta else False
    
    results["results"]["technical"]["robots_meta_tag_exists"] = {
        "value": robots_meta_value,
        "status": "Good" if robots_meta else "Needs Improvement",
        "rating": 8 if robots_meta else 5,
        "reason": "Robots meta tag present" if robots_meta else "Missing robots meta tag",
        "category":"High Priority"
    }
    logger.info(f"robots_meta_tag_exists - Results: {results.get('results', {}).get('technical')}")


@measure_execution_time
def check_noindex_tag_check(soup: BeautifulSoup, results: Dict[str, Any]) -> None:
    """
    Checks for the presence of the 'noindex' directive in the robots meta tag.
    This tag controls whether search engines should index the page.

    Args:
        soup: A BeautifulSoup object representing the parsed HTML.
        results: A dictionary to store the analysis results. It is expected to
                have a structure where results["results"]["technical"] is a
                dictionary to which the analysis outcome will be added.
    """
    robots_meta = soup.find("meta", attrs={"name": "robots"})
    noindex = robots_meta and "noindex" in robots_meta.get("content", "").lower()
    result_data = {
        "value": noindex,
        "status": "Needs Improvement" if noindex else "Good", 
        "rating": 1 if noindex else 10, 
        "reason": "Page is noindex" if noindex else "Page is indexable",
        "category":"High Priority",
        }

    logger.warning(f"Before setting noindex_tag_check - Results: {results.get('results', {}).get('technical')}")
    results["results"]["technical"]["noindex_tag_check"] = result_data
    logger.warning(f"After setting noindex_tag_check - Results: {results.get('results', {}).get('technical')}")



@measure_execution_time
def check_nofollow_tag_check(soup, results):
# Explicit section initialization
    technical_section = results["results"].setdefault("technical", {})
    # Clear attribute check
    robots_meta = soup.find("meta", attrs={"name": "robots"})
    content = robots_meta.get("content", "").lower() if robots_meta else ""
    # Explicit nofollow check
    nofollow = "nofollow" in content
    technical_section["nofollow_tag_check"] = {
        "value": nofollow,
        "status": "Needs Improvement" if nofollow else "Good",
        "rating": 1 if nofollow else 10,
        "reason": "Links are nofollowed" if nofollow else "Links are followed",
        "category":"Average Priority",
    }


@measure_execution_time
def check_image_dimensions_specified(soup: BeautifulSoup, results: dict) -> None:
    """
    Checks if all images have specified dimensions (width/height attributes).
    
    Args:
        soup: BeautifulSoup parsed document
        results: Results dictionary to update
    """
    images = soup.find_all('img')
    total_images = len(images)
    
    # Handle no images case first
    if not images:
        results["results"]["content"]["image_dimensions_specified"] = {
            "value": True,
            "status": "Not Applicable",
            "rating": 10,
            "reason": "No images found on page",
            "details": {
                "total_images": 0,
                "missing_width": 0,
                "missing_height": 0
            },
            "category":"Average Priority",
        }
        return

    missing_width = 0
    missing_height = 0
    missing_both = 0

    for img in images:
        has_width = bool(img.get('width', '').strip())
        has_height = bool(img.get('height', '').strip())
        
        if not has_width and not has_height:
            missing_both += 1
        else:
            if not has_width: missing_width += 1
            if not has_height: missing_height += 1

    total_issues = missing_both + missing_width + missing_height
    compliance_ratio = (total_images - missing_both) / total_images  # Full compliance requires both dimensions

    # Calculate rating (8 = perfect, 1 = worst)
    if total_issues == 0:
        status = "Good"
        rating = 8
        reason = "All images have dimensions specified"
    else:
        status = "Needs Improvement"
        rating = max(1, min(7, int(8 * compliance_ratio)))
        reason = (
            f"{missing_both} images missing both dimensions, " 
            f"{missing_width} missing width, {missing_height} missing height"
        )

    results["results"]["content"]["image_dimensions_specified"] = {
        "value": total_issues == 0,
        "status": status,
        "rating": rating,
        "reason": reason,
        "details": {
            "total_images": total_images,
            "missing_width": missing_width,
            "missing_height": missing_height,
            "missing_both": missing_both,
            "compliance_percent": f"{compliance_ratio:.0%}"
        },
        "category":"Average Priority",

    }

@measure_execution_time
def check_nofollow_on_external_links(soup: BeautifulSoup, results: Dict[str, Any]) -> None:
    """
    Analyzes external links on the webpage to check if they have the 'nofollow'
    attribute in their 'rel' attribute. Using 'nofollow' for untrusted external
    links is an SEO best practice.

    Args:
        soup: A BeautifulSoup object representing the parsed HTML.
        results: A dictionary to store the analysis results. It is expected to
                have a structure where results["results"]["links"] is a
                dictionary to which the analysis outcome will be added.
    """
    external_links: List[BeautifulSoup] = [
        a for a in soup.find_all("a", href=True) if a.get("href").startswith("http")
    ]
    nofollow_links: List[BeautifulSoup] = [
        link for link in external_links if link.get("rel") and "nofollow" in link.get("rel")
    ]
    total_external = len(external_links)
    nofollow_count = len(nofollow_links)
    nofollow_ratio = (nofollow_count / total_external) if total_external > 0 else 1.0  # Default to 1 if no external links

    status = "Good" if nofollow_ratio >= 0.75 else "Needs Improvement" if total_external > 0 else "Not Applicable"
    rating = 9 if nofollow_ratio >= 0.75 else (5 if total_external > 0 else 10)
    reason = (
        f"{nofollow_count} out of {total_external} external links have 'nofollow' ({(nofollow_ratio * 100):.2f}%)"
        if total_external > 0
        else "No external links found to check for 'nofollow'"
    )

    results["results"]["links"]["nofollow_on_external_links"] = {
        "value": nofollow_count,
        "status": status,
        "rating": rating,
        "reason": reason,
        "total_external_links": total_external,
        "nofollow_percentage": f"{(nofollow_ratio * 100):.2f}%" if total_external > 0 else "N/A",
        "category":"Average Priority",
    }

@measure_execution_time
def check_gzip_compression(base_url, results,response):
    try:
        # Send HTTP request with a timeout to avoid hanging
        response = requests.get(base_url, timeout=10)
        
        # Check Content-Encoding header
        content_encoding = response.headers.get("Content-Encoding", "").lower()
        is_gzip_enabled = "gzip" in content_encoding
        
        # Verify decompression
        if is_gzip_enabled:
            try:
                # Check if the response content is empty
                if not response.content:
                    results["results"]["performance"]["gzip_compression_enabled"] = {
                        "value": False,
                        "status": "Needs Improvement",
                        "rating": 5,
                        "reason": "Gzip compression is declared, but the response body is empty.",
                        "category":"High Priority",
                    }
                    return
                
                # Attempt to decompress the response body
                decompressed_data = gzip.GzipFile(fileobj=io.BytesIO(response.content)).read()
                
                # If decompression succeeds, Gzip is working correctly
                results["results"]["performance"]["gzip_compression_enabled"] = {
                    "value": True,
                    "status": "Good",
                    "rating": 10,
                    "reason": "Gzip compression is enabled and working correctly.",
                    "category":"High Priority",
                }
            except Exception as e:
                # If decompression fails, Gzip is declared but not working
                results["results"]["performance"]["gzip_compression_enabled"] = {
                    "value": False,
                    "status": "Needs Improvement",
                    "rating": 5,
                    "reason": f"Gzip compression is declared but failed to decompress the response body: {str(e)}",
                    "category":"High Priority",

                }
        else:
            # Gzip is not declared in the headers
            results["results"]["performance"]["gzip_compression_enabled"] = {
                "value": False,
                "status": "Needs Improvement",
                "rating": 5,
                "reason": "Gzip compression is not enabled. Enable Gzip to reduce file sizes.",
                "category":"High Priority",
            }

    except requests.exceptions.RequestException as e:
        # Handle network-related errors
        results["results"]["performance"]["gzip_compression_enabled"] = {
            "value": False,
            "status": "Error",
            "rating": 1,
            "reason": f"A network error occurred while checking Gzip compression: {str(e)}",
            "category":"High Priority",
        }
    except Exception as e:
        # Handle unexpected errors
        results["results"]["performance"]["gzip_compression_enabled"] = {
            "value": False,
            "status": "Error",
            "rating": 1,
            "reason": f"An unexpected error occurred while checking Gzip compression: {str(e)}",
            "category":"High Priority",
        }


@measure_execution_time
async def check_browser_caching_enabled(response, results,base_url):
    logger.info("starting Checking browser caching headers")

    response = requests.get(base_url, timeout=10)
    # First check if response is None
    if response is None:
        results["results"]["performance"]["browser_caching_enabled"] = {
            "value": False,
            "status": "Error",
            "rating": 0,
            "reason": "Could not check browser caching - no response available",
            "category":"High Priority",
        }
        return
    # Check for cache control headers
    cache_control = response.headers.get('Cache-Control')
    expires = response.headers.get('Expires')
    etag = response.headers.get('ETag')
    last_modified = response.headers.get('Last-Modified')
    
    # Initialize with default values
    is_enabled = False
    status = "Poor"
    rating = 0
    reason = "Browser caching is not properly configured"
    
    # Check if any caching mechanism is enabled
    if cache_control:
        if any(directive in cache_control for directive in ['max-age=', 'public', 's-maxage=']):
            is_enabled = True
            status = "Good"
            rating = 10
            reason = "Browser caching is enabled via Cache-Control"
    elif expires:
        is_enabled = True
        status = "Good"
        rating = 8
        reason = "Browser caching is enabled via Expires header"
    elif etag or last_modified:
        is_enabled = True
        status = "Fair"
        rating = 6
        reason = "Browser caching is enabled via validation headers (ETag/Last-Modified)"
    
    # Update results dictionary
    results["results"]["performance"]["browser_caching_enabled"] = {
        "value": is_enabled,
        "status": status,
        "rating": rating,
        "reason": reason,
        "category":"High Priority",
    }
    logger.info(f"browser_caching_enabled is completed - Results: {results.get('results', {}).get('performance')}")



@measure_execution_time
async def check_xml_sitemap_exists(base_url, results):
    sitemap_url = urljoin(base_url, "sitemap.xml")
    async with aiohttp.ClientSession() as session:      #allows to make HTTP request without blocking the program
        try:
            async with session.get(base_url, timeout=ClientTimeout(total=10)) as response:
                results["results"]["technical"]["xml_sitemap_exists"] = {
                    "value": response.status == 200,
                    "status": "Good" if response.status == 200 else "Needs Improvement",
                    "rating": 9 if response.status == 200 else 5,
                    "reason": "XML sitemap found" if response.status == 200 else "XML sitemap missing",
                    "category":"High Priority",
                }
        except Exception as e:
            return None


@measure_execution_time
def check_keyword_in_title(soup, results, target_keyword):
    """
    Checks if the target keyword exists in the title of a web page.
    Updates the 'results' dictionary with the keyword check results.
    """
    try:
        # Ensure the results dictionary has the required structure
        if "results" not in results:
            results["results"] = {}
        if "content" not in results["results"]:
            results["results"]["content"] = {}

        # Extract the title tag from the soup object
        title_tag = soup.title

        # Check if the title tag exists and get its text in lowercase
        title_text = title_tag.get_text().strip().lower() if title_tag else ""

        # Validate the target keyword
        if not target_keyword or not isinstance(target_keyword, str) or not target_keyword.strip():
            results["results"]["content"]["keyword_in_title"] = {
                "value": False,
                "status": "poor",
                "rating": 1,
                "reason": "Invalid or missing target keyword its important for SEO",
                "category":"High Priority",
            }
            return

        # Normalize the target keyword
        target_keyword = target_keyword.strip().lower()

        # Check if the keyword is in the title
        keyword_in_title = target_keyword in title_text

        # Update the results dictionary
        results["results"]["content"]["keyword_in_title"] = {
            "value": keyword_in_title,
            "status": "Good" if keyword_in_title else "Needs Improvement",
            "rating": 10 if keyword_in_title else 5,
            "reason": "Keyword in title" if keyword_in_title else "Keyword not in title",
             "category":"High Priority",
        }

    except Exception as e:
        # Log any unexpected errors
        results["results"]["content"]["keyword_in_title"] = {
            "value": False,
            "status": "Error",
            "rating": 1,
            "reason": f"Failed to check keyword in title: {str(e)}",
             "category":"High Priority",
        }

@measure_execution_time
def check_keyword_in_h1(soup, results, target_keyword):
    # Initialize results section safely
    content_section = results["results"].setdefault("content", {})
    
    # Handle missing keyword case
    if not target_keyword:
        content_section["keyword_in_h1"] = {
            "value": None,
            "status": "Not Checked",
            "rating": 5,
            "reason": "No target keyword provided",
             "category":"High Priority",
        }
        return

    # Find and process H1 tags
    h1_tags = soup.find_all('h1')
    target_lower = target_keyword.lower()
    
    # Check for exact word matches
    keyword_found = False
    for h1 in h1_tags:
        h1_text = h1.get_text().lower()
        if re.search(rf'\b{re.escape(target_lower)}\b', h1_text):
            keyword_found = True
            break  # No need to check further if found

    # Build results
    content_section["keyword_in_h1"] = {
        "value": keyword_found,
        "status": "Good" if keyword_found else "Needs Improvement",
        "rating": 10 if keyword_found else 5,
        "reason": ("Keyword found in H1" if keyword_found 
                else f"Keyword '{target_keyword}' missing from all H1 tags"),
        "h1_count": len(h1_tags),
        "h1_samples": [h1.get_text().strip()[:50] for h1 in h1_tags[:3]],  # For debugging,
        "category":"High Priority",
    }

@measure_execution_time
async def check_image_file_size_optimized(soup: BeautifulSoup, results: Dict[str, Any], base_url: str) -> None:
    """
    Asynchronously checks if the file size of the first 10 images on the page
    is within an acceptable limit (<= 150 kB). It identifies images that are
    too large or fail to load.
    """
    images: List[BeautifulSoup] = soup.find_all("img")[:10]

    broken_images_details: List[str] = []

    def is_data_uri(img_url: str) -> bool:
        """Checks if the image URL is a data URI."""
        return img_url.startswith("data:")

    async def fetch_image_size(session: aiohttp.ClientSession, image_url: str) -> Optional[str]:
        """Asynchronously fetches the size of an image using a HEAD request."""
        try:
            async with session.head(image_url, timeout=ClientTimeout(total=5)) as response:
                if response.status == 200:
                    filesize_bytes = response.headers.get("content-length") #content-length is used to get the size of the image
                    if filesize_bytes:
                        filesize_kb = int(filesize_bytes) / 1024
                        if filesize_kb > 150:
                            return f"{image_url} ({filesize_kb:.2f} kB)"
                        else:
                            logger.info(f"Image size within limit: {image_url} ({filesize_kb:.2f} kB)")
                            return None
                    else:
                        logger.warning(f"No content-length header for: {image_url}")
                        return f"{image_url} (No content-length header)"
                else:
                    logger.warning(f"Image request failed: {image_url} (HTTP{response.status})")
                    return f"{image_url} (HTTP{response.status})"
        except asyncio.TimeoutError:
            logger.warning(f"Timeout fetching image size for {image_url}")
            return f"{image_url} (Timeout)"
        except Exception as e:
            logger.error(f"Error fetching image size for {image_url}: {type(e).__name__} - {str(e)}")
            return f"{image_url} (Error: {type(e).__name__})"

    async with aiohttp.ClientSession() as session:
        tasks = []
        for img in images:
            img_url_raw = img.get("src", "")
            if not img_url_raw:
                continue
            #convert the relative URL to absolute URL using urljoin
            img_url = urljoin(base_url, img_url_raw)
            logger.info(f"completed converting image URL: {img_url}")

            if is_data_uri(img_url):  # Check if the image URL is a data URI
                # Skip data URIs and log the reason
                logger.info(f"Skipping data URI: {img_url}")
                continue

            logger.info(f"Adding image URL to tasks: {img_url}")
            tasks.append(fetch_image_size(session, img_url))

        # Execute all tasks concurrently
        logger.info(f"Starting to fetch image sizes for {len(tasks)} images")
        broken_images_results = await asyncio.gather(*tasks)
        
        # Filter out working images and keep only broken images
        broken_images_details = [result for result in broken_images_results if result]

    is_optimized = not broken_images_details

    results["results"]["content"]["image_file_size_optimized"] = {
        "value": is_optimized,
        "status": "Good" if is_optimized else "Needs Improvement",
        "rating": 9 if is_optimized else 5,
        "reason": "First 10 images are within the size limit or data URIs" if is_optimized else (
            f"Large or broken images found in the first 10 images: {len(broken_images_details)}" if broken_images_details else "No images found"
        ),
        "details": broken_images_details if broken_images_details else None,
        "category":"Average Priority",
    }
    logger.info(f"Image file size optimization check completed. Optimized: {is_optimized}")


@measure_execution_time
async def check_broken_internal_links(soup: BeautifulSoup, results: Dict[str, Any], base_url: str) -> None:
    """
    Asynchronously checks for broken internal links (returning a 4xx or 5xx
    status code) on the webpage.

    Args:
        soup: A BeautifulSoup object representing the parsed HTML.
        results: A dictionary to store the analysis results. The broken internal
                links status will be added under
                results["results"]["links"]["broken_internal_links"].
        base_url: The URL of the webpage being analyzed, used to resolve relative
            internal links.
    """
    # Extract raw internal links (relative links starting with '/' or './')
    internal_links_raw: List[str] = [
        a.get("href") for a in soup.find_all("a", href=True)
        if a.get("href").startswith(("/", "./"))
    ]
    
    # Convert relative links to absolute links using the base URL
    internal_links: List[str] = [urljoin(base_url, link) for link in internal_links_raw if link]
    broken_links: List[str] = []
    timeouts: List[str] = []  # To log timeouts separately

    async def check_link_with_retries(session: aiohttp.ClientSession, link: str, retries: int = 3) -> Optional[str]:
        """Asynchronously checks the status code of a single link with retries."""
        for attempt in range(retries):
            try:
                async with session.head(link, allow_redirects=True, timeout=ClientTimeout(total=10)) as response:
                    if response.status >= 400:
                        return f"{link} ({response.status})"  # Link is broken
                    return None  # Link is working fine
            except asyncio.TimeoutError:
                if attempt == retries - 1:  # Last attempt
                    return f"{link} (Timeout after {retries} retries)"
            except aiohttp.ClientError as e:
                return f"{link} (Client Error: {str(e)})"
            except Exception as e:
                return f"{link} (Error: {str(e)})"

    # Create an HTTP session and check all internal links asynchronously
    async with aiohttp.ClientSession() as session:
        tasks = [check_link_with_retries(session, link) for link in internal_links]
        broken_links_results = await asyncio.gather(*tasks)

        # Separate broken links and timeouts
        for result in broken_links_results:
            if result:
                if "(Timeout" in result:
                    timeouts.append(result)  # Log timeouts separately
                else:
                    broken_links.append(result)  # Add to broken links

    # Calculate the number of broken links and timeouts
    num_broken_links = len(broken_links)
    num_timeouts = len(timeouts)

    # Add results to the `results` dictionary
    if num_broken_links > 0 or num_timeouts > 0:
        results["results"]["links"]["broken_internal_links"] = {
            "value": True,
            "status": "Needs Improvement",
            "rating": 1,
            "reason": f"{num_broken_links} broken internal link(s) found. {num_timeouts} link(s) timed out.",
            "details": {
                "broken_links": broken_links,  # List of actual broken links
                "timeouts": timeouts  # List of links that timed out
            },
            "category":"High Priority",
        }
    else:
        results["results"]["links"]["broken_internal_links"] = {
            "value": False,
            "status": "Good",
            "rating": 9,
            "reason": "No broken internal links found.",
            "category":"High Priority",
        }

    # Log the results
    logger.info(f"Broken internal links check completed. Broken links: {num_broken_links}, Timeouts: {num_timeouts}")
    if broken_links:
        logger.info(f"Broken links: {num_broken_links}")
    if timeouts:
        logger.info(f"Timeouts: {timeouts}")



@measure_execution_time
async def check_broken_external_links(soup, results, base_url):
    # Helper function to extract external links
    def extract_external_links(soup, base_url):
        base_domain = urlparse(base_url).netloc
        return [
            a.get("href") for a in soup.find_all("a", href=True)
            if a.get("href").startswith("http") and urlparse(a.get("href")).netloc != base_domain
        ]

    # Helper function to check a single link
    async def check_link(session, link, retries=3):
        for attempt in range(retries):
            try:
                async with session.head(link, allow_redirects=True, timeout=ClientTimeout(total=10)) as response:
                    if response.status >= 400:
                        return f"{link} ({response.status})"
                    return None  # Link is working fine
            except asyncio.TimeoutError:
                if attempt == retries - 1:  # Last attempt
                    return f"{link} (Timeout after {retries} retries)"
            except aiohttp.ClientError as e:
                return f"{link} (Client Error: {str(e)})"
            except Exception as e:
                return f"{link} (Error: {str(e)})"
        return None

    # Extract external links
    external_links = extract_external_links(soup, base_url)

    # Check all external links asynchronously
    async with aiohttp.ClientSession() as session:
        tasks = [check_link(session, link) for link in external_links]
        results_list = await asyncio.gather(*tasks)

    # Separate working and broken links
    broken_links = [result for result in results_list if result]
    working_links = [link for link, result in zip(external_links, results_list) if not result]

    # Add results to the dictionary
    if broken_links:
        results['results']['links']['broken_external_links'] = {
            "value": False,
            "status": "Needs Improvement",
            "rating": 1,
            "reason": f"{len(broken_links)} broken external link(s) found",
            "details": {
                "broken_links": broken_links,
                # "working_links": working_links
            },
            "category":"Average Priority",

        }
    else:
        results["results"]["links"]["broken_external_links"] = {
            "value": True,
            "status": "Good",
            "rating": 9,
            "reason": "No broken external links found",
            "category":"Average Priority",
        }

    # Log the results
    logger.info(f"Broken external links check completed. Broken links: {len(broken_links)}, Working links: {len(working_links)}")

@measure_execution_time
async def check_external_linking_quality(soup, results, base_url):
    # Reuse the same `extract_external_links` and `check_link` functions
    def extract_external_links(soup, base_url):
        base_domain = urlparse(base_url).netloc
        return [
            a.get("href") for a in soup.find_all("a", href=True)
            if a.get("href").startswith("http") and urlparse(a.get("href")).netloc != base_domain
        ]

    async def check_link(session, link, retries=3):
        for attempt in range(retries):
            try:
                async with session.head(link, allow_redirects=True, timeout=ClientTimeout(total=10)) as response:
                    if response.status >= 400:
                        return f"{link} ({response.status})"
                    return None  # Link is working fine
            except asyncio.TimeoutError:
                if attempt == retries - 1:  # Last attempt
                    return f"{link} (Timeout after {retries} retries)"
            except aiohttp.ClientError as e:
                return f"{link} (Client Error: {str(e)})"
            except Exception as e:
                return f"{link} (Error: {str(e)})"
        return None

    # Extract external links
    external_links = extract_external_links(soup, base_url)

    # Check all external links asynchronously
    async with aiohttp.ClientSession() as session:
        tasks = [check_link(session, link) for link in external_links]
        results_list = await asyncio.gather(*tasks)

    # Separate working and broken links
    broken_links = [result for result in results_list if result]
    working_links = [link for link, result in zip(external_links, results_list) if not result]

    # Add results to the dictionary
    total_links = len(external_links)
    broken_count = len(broken_links)
    working_count = len(working_links)

    results["results"]["links"]["external_linking_quality"] = {
        "value": total_links,
        "status": "Good" if broken_count == 0 else "Needs Improvement",
        "rating": 9 if broken_count == 0 else 5,
        "reason": f"Page contains {total_links} external link(s). {working_count} working, {broken_count} broken.",
        "details": {
            "working_links": working_links,
            "broken_links": broken_links
        },
        "category":"High Priority",
    }

    # Log the results
    logger.info(f"External linking quality check completed. Total links: {total_links}, Working: {working_count}, Broken: {broken_count}")

@measure_execution_time
async def check_redirects_minimized(base_url: str, results: Dict[str, Any]) -> None:
    """
    Asynchronously checks if the number of redirects for a given URL is within
    an acceptable limit (<= 2). Excessive redirects can negatively impact
    page load speed and SEO.

    Args:
        url: The URL to check for redirects.
        results: A dictionary to store the analysis results. The redirect
                minimization status will be added under
                results["results"]["performance"]["redirects_minimized"].
    """
    performance_results = results.setdefault("results", {}).setdefault("performance", {})
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(base_url, allow_redirects=True, timeout=ClientTimeout(total=10)) as response:
                redirect_count = len(response.history)
                performance_results["redirects_minimized"] = {
                    "value": redirect_count <= 2,
                    "status": "Good" if redirect_count <= 2 else "Needs Improvement",
                    "rating": 10 if redirect_count <= 2 else 5,
                    "reason": f"{redirect_count} redirects encountered" if redirect_count > 0 else "No redirects",
                    "details": [str(res.url) for res in response.history],
                    "category":"High Priority",
                }
                logger.info(f"Redirect check for {base_url} completed. Redirect count: {redirect_count}")
    except aiohttp.ClientError as e:
        error_message = f"Failed to check redirects for {base_url}: {type(e).__name__} - {str(e)}"
        performance_results["redirects_minimized"] = {
            "value": "Error",
            "status": "Error",
            "rating": 1,
            "reason": error_message,
            "category":"High Priority",
        }
        logger.error(error_message)
        
    except asyncio.TimeoutError:
        error_message = f"Timeout while checking redirects for {base_url}"
        performance_results["redirects_minimized"] = {
            "value": "Error",
            "status": "Error",
            "rating": 1,
            "reason": error_message,
            "category":"High Priority",
        }
        logger.error(error_message)
    except Exception as e:
        error_message = f"Unexpected error while checking redirects for {base_url}: {type(e).__name__} - {str(e)}"
        performance_results["redirects_minimized"] = {
            "value": "Error",
            "status": "Error",
            "rating": 1,
            "reason": error_message,
            "category":"High Priority",
        }
        logger.exception(error_message)


@measure_execution_time
def check_keyword_density(soup: BeautifulSoup, results: Dict[str, Any], target_keyword: Optional[str]) -> None:
    """
    Calculates the keyword density of the target keyword in the text content
    of the webpage. Updates the 'results' dictionary under the 'content' key.

    Args:
        soup: A BeautifulSoup object representing the parsed HTML.
        results: A dictionary to store the analysis results. The keyword
                density will be added under
                results["results"]["content"]["keyword_density"].
        target_keyword: The keyword to calculate the density for (case-insensitive).
                        If None or empty, an informational result is added.
    """

    content_results = results.setdefault("results", {}).setdefault("content", {})
    if target_keyword:
        text = soup.get_text(separator=' ', strip=True).lower()
        words = re.findall(r'\b\w+\b', text)
        keyword_lower = target_keyword.lower()
        keyword_count = Counter(words)[keyword_lower]
        total_words = len(words)
        density = (keyword_count / total_words) * 100 if total_words > 0 else 0
        rounded_density = round(density, 2)
        status = "Good" if 1 <= rounded_density <= 3 else "Needs Improvement"
        rating = 9 if 1 <= rounded_density <= 3 else 5
        reason = f"Keyword density for '{target_keyword}': {rounded_density}%"
        content_results["keyword_density"] = {
            "value": rounded_density,
            "status": status,
            "rating": rating,
            "reason": reason,
             "category":"High Priority",
        }
        logger.info(f"Keyword density for '{target_keyword}': {rounded_density}%")
    else:
        content_results["keyword_density"] = {
            "value": "No target keyword",
            "status": "poor",
            "rating": 3,
            "reason": "No target keyword provided for density analysis",
            "category":"High Priority",
        }
        logger.info("Keyword density check skipped: no target keyword provided.")




@measure_execution_time
async def check_content_freshness(base_url, soup, results):
        freshness_date = None   # stores the lates update date if found

        async def fetch_last_modified():   
            nonlocal freshness_date       # allows modified freshness date in this function
            try:
                async with aiohttp.ClientSession() as session:  #open async http session
                    async with session.head(base_url, timeout=ClientTimeout(total=5)) as response:   #sends request head
                        last_modified = response.headers.get("Last-Modified")
                        if last_modified:
                            freshness_date = parser.parse(last_modified)
            except Exception:
                pass

        async def check_meta_tags():
            nonlocal freshness_date
            relevant_meta_tags = soup.select('meta[name="article:published_time"], meta[name="article:modified_time"], meta[name="date"]')
            for meta in relevant_meta_tags:
                try:
                    freshness_date = parser.parse(meta.get("content"))
                    break
                except ValueError:
                    continue

        async def check_content_dates():
            nonlocal freshness_date
            relevant_sections = soup.find_all(["h1", "h2", "h3", "p"])
            body_text = " ".join(section.get_text() for section in relevant_sections)
            content_dates = re.findall(r"\b\d{4}-\d{2}-\d{2}\b", body_text)
            if content_dates:
                try:
                    freshness_date = parser.parse(content_dates[0])
                except ValueError:
                    pass

        await asyncio.gather(fetch_last_modified(), check_meta_tags(), check_content_dates())

        # Decide freshness status
        if freshness_date:
            days_old = (datetime.utcnow().replace(tzinfo=freshness_date.tzinfo) - freshness_date).days
            status = "Good" if days_old <= 30 else "Needs Improvement"
            rating = 9 if days_old <= 30 else 5
            reason = f"Last update {days_old} days ago"
        else:
            status = "poor"
            rating = 4
            reason = "No date information available.Consider adding a Last-Modified header or meta tags."

        results["results"]["content"]["content_freshness"] = {
            "value": freshness_date.strftime("%Y-%m-%d") if freshness_date else "Not Found",
            "status": status,
            "rating": rating,
            "reason": reason,
            "category":"Average Priority",
        }

    
@measure_execution_time
async def check_https_redirect(base_url: str, results: Dict[str, Any]) -> None:
    """
    Checks if an HTTP URL redirects to HTTPS and updates the results dictionary.
    Skips the check if the URL is already HTTPS.
    Uses asynchronous HTTP requests to avoid blocking the event loop.
    """
    try:
        # If the URL is already HTTPS, skip the check
        if base_url.startswith("https://"):
            logger.info(f"URL is already HTTPS: {base_url}")
            return

        # Construct the HTTPS URL
        https_url = base_url.replace("http://", "https://", 1)
        logger.info(f"Checking if HTTP URL redirects to HTTPS: {https_url}")

        # Use aiohttp for asynchronous HTTP requests
        async with aiohttp.ClientSession() as session:
            # First, check if the HTTPS URL is reachable
            try:
                async with session.head(https_url, timeout=ClientTimeout(total=5)) as head_response:
                    if head_response.status >= 400:
                        logger.warning(f"HTTPS URL is unreachable: {https_url}. Status code: {head_response.status}")
                        results["results"]["security"]["https_redirect"] = {
                            "value": False,
                            "status": "Error",
                            "rating": 1,
                            "reason": f"HTTPS URL is unreachable. Status code: {head_response.status}"
                        }
                        return
            except Exception as e:
                logger.error(f"Failed to reach HTTPS URL: {https_url}. Error: {str(e)}")
                results["results"]["security"]["https_redirect"] = {
                    "value": False,
                    "status": "Error",
                    "rating": 1,
                    "reason": f"Failed to reach HTTPS URL: {str(e)}"
                }
                return

            # Check if the HTTP URL redirects to HTTPS
            async with session.get(base_url, allow_redirects=False, timeout=ClientTimeout(total=5)) as response:
                valid_redirect_codes = [301, 302, 307, 308]
                is_redirect = response.status in valid_redirect_codes
                redirect_location = response.headers.get("Location", "")

                # Ensure the redirect location is HTTPS
                if is_redirect and redirect_location.startswith("https://"):
                    results["results"]["security"]["https_redirect"] = {
                        "value": True,
                        "status": "Good",
                        "rating": 10,
                        "reason": "HTTP redirects to HTTPS"
                    }
                else:
                    results["results"]["security"]["https_redirect"] = {
                        "value": False,
                        "status": "Needs Improvement",
                        "rating": 5,
                        "reason": "HTTP does not redirect to HTTPS"
                    }

    except aiohttp.ClientError as e:
        # Handle network-related errors
        logger.error(f"Network error while checking HTTPS redirect: {str(e)}")
        results["results"]["security"]["https_redirect"] = {
            "value": False,
            "status": "Error",
            "rating": 1,
            "reason": f"Network error: {str(e)}"
        }

    except Exception as e:
        # Handle unexpected errors
        logger.exception(f"Unexpected error while checking HTTPS redirect: {str(e)}")
        results["results"]["security"]["https_redirect"] = {
            "value": False,
            "status": "Error",
            "rating": 1,
            "reason": f"Unexpected error: {str(e)}"
        }

@measure_execution_time
def check_internal_linking_depth(soup, results):
    internal_links = (a['href'] for a in soup.select('a[href^="/"]'))
    
    # Count up to 6 and stop early if needed
    link_count = sum(1 for _ in islice(internal_links, 6))

    results["results"]["links"]["internal_linking_depth"] = {
        "value": link_count,
        "status": "Good" if link_count > 5 else "Needs Improvement",
        "rating": 9 if link_count > 5 else 5,
        "reason": f"Page contains {link_count} internal links.",
        "category":"Average Priority",
    }


@measure_execution_time
async def check_page_depth(base_url, results):
    logger.info(f"Checking page depth for {base_url}")
    try:
        parsed_url = urlparse(base_url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        base_domain = parsed_url.netloc
        visited = set()
        queue = deque([(base_url, 0)])
        max_depth = 3
        max_concurrent_requests = 5
        max_total_urls = 100  # Safety limit
        semaphore = asyncio.Semaphore(max_concurrent_requests)
        delay = 0.1  # Be polite to servers

        async def fetch_links(session, current_url, depth):
            try:
                async with semaphore:
                    await asyncio.sleep(delay)  # Rate limiting
                    async with session.get(
                        current_url,
                        timeout=ClientTimeout(total=5),  # Timeout set to 5 seconds
                        allow_redirects=True
                    ) as response:
                        if response.status != 200:
                            logger.warning(f"Non-200 status for {current_url}: {response.status}")
                            return set()

                        final_url = str(response.url)
                        if final_url != current_url:
                            # Handle redirects
                            if final_url in visited or not final_url.startswith(base_url):
                                return set()
                            return {final_url}

                        soup = BeautifulSoup(await response.text(), "lxml")
                        links = set()
                        for a in soup.find_all("a", href=True):
                            href = a.get("href")
                            if not href or href.startswith("#"):
                                continue

                            # Normalize URL
                            link = urljoin(current_url, href)
                            # Remove query parameters and fragments
                            link = urlparse(link)._replace(query="", fragment="").geturl()
                            if link.startswith(base_url) and link not in visited:
                                links.add((link, depth + 1))  # Store link with its depth
                        return links
            except asyncio.TimeoutError:
                logger.error(f"Timeout while fetching {current_url}")
                return set()
            except aiohttp.ClientError as e:
                logger.error(f"Client error while fetching {current_url}: {str(e)}")
                return set()
            except Exception as e:
                logger.exception(f"Unexpected error while fetching {current_url}: {str(e)}")
                return set()

        max_reached_depth = 0
        processed_urls = 0
        async with aiohttp.ClientSession() as session:
            tasks = set()
            while queue and processed_urls < max_total_urls:
                current_url, depth = queue.popleft()
                if current_url in visited:
                    continue

                visited.add(current_url)
                processed_urls += 1
                max_reached_depth = max(max_reached_depth, depth)

                if depth < max_depth:
                    task = asyncio.create_task(fetch_links(session, current_url, depth))
                    tasks.add(task)
                    task.add_done_callback(tasks.discard)

                    # Process completed tasks periodically
                    if len(tasks) >= max_concurrent_requests:
                        done, _ = await asyncio.wait(
                            tasks,
                            return_when=asyncio.FIRST_COMPLETED
                        )
                        for task in done:
                            new_links = await task
                            for link, link_depth in new_links:
                                if link not in visited and link not in (url for url, _ in queue):
                                    queue.append((link, link_depth))

            # Process any remaining tasks
            if tasks:
                done, _ = await asyncio.wait(tasks)
                for task in done:
                    new_links = await task
                    for link, link_depth in new_links:
                        if link not in visited and link not in (url for url, _ in queue):
                            queue.append((link, link_depth))

        results["results"]["url"]["page_depth"] = {
            "value": max_reached_depth,
            "status": "Good" if max_reached_depth <= 3 else "Needs Improvement",
            "rating": 10 if max_reached_depth <= 3 else 5,
            "reason": f"Maximum page depth reached: {max_reached_depth}",
            "processed_urls": processed_urls,
            "category":"High Priority",
        }
    except Exception as e:
        results["results"]["url"]["page_depth"] = {
            "value": "Error",
            "status": "Error",
            "rating": 1,
            "reason": f"Error calculating page depth: {str(e)}",
        }
        logger.exception(f"Unexpected error in check_page_depth: {str(e)}")
                

@measure_execution_time
def check_content_readability(soup, results):
    text = soup.get_text(separator=' ', strip=True)
    word_count = len(text.split())
    readability_score = word_count / 100  # Simplified metric
    results["results"]["content"]["content_readability"] = {
        "value": readability_score,
        "status": "Good" if readability_score > 5 else "Needs Improvement",
        "rating": 9 if readability_score > 5 else 5,
        "reason": f"Readability Score: {readability_score}",
         "category":"Average Priority",
    }


@measure_execution_time
def check_social_meta_tags(soup, results):
    social_meta_tags=sum(1 for tag in soup.find_all("meta")
                        if tag.get("property", "").startswith("og:")
                        or tag.get("name","").startswith("Twitter:"))
    
    has_social_tags=social_meta_tags>0
    results["results"]["meta_tags"]["social_meta_tags"]={
        "value":has_social_tags,
        "status":"Good" if has_social_tags else "Needs to improvement",
        "rating":8 if has_social_tags else 5,
        "reasons":"Social meta tags present" if has_social_tags else "Missing social meta tags",
        "category":"Average Priority",

    }


@measure_execution_time
async def check_favicon_exists(soup, base_url, results):
    # Helper function to check favicon existence asynchronously
    async def fetch_favicon(session, favicon_url):
        try:
            async with session.head(favicon_url, timeout=ClientTimeout(total=2)) as response:
                if response.status == 200:
                    return favicon_url
        except Exception:
            pass
        return None

    # Check if favicon is declared in HTML
    favicon_tag = soup.find("link", rel=lambda r: r and "icon" in r.lower())
    declared_favicon_url = urljoin(base_url, favicon_tag["href"]) if favicon_tag and "href" in favicon_tag.attrs else None

    # Fallback: Check /favicon.ico in root directory
    root_favicon_url = urljoin(base_url, "/favicon.ico")

    # Perform concurrent checks for both declared favicon and fallback
    async with aiohttp.ClientSession() as session:
        tasks = []
        if declared_favicon_url:
            tasks.append(fetch_favicon(session, declared_favicon_url))
        tasks.append(fetch_favicon(session, root_favicon_url))

        # Gather results from all tasks
        results_list = await asyncio.gather(*tasks)

    # Determine the final result
    favicon_found = next((base_url for base_url in results_list if base_url), None)
    if favicon_found:
        results["results"]["meta_tags"]["favicon_exists"] = {
            "value": favicon_found,
            "status": "Good",
            "rating": 10,
            "reason": f"Favicon found and accessible",
            "category":"Average Priority",
        }
    else:
        results["results"]["meta_tags"]["favicon_exists"] = {
            "value": False,
            "status": "Poor",
            "rating": 5,
            "reason": "Favicon not found",
            "category":"Average Priority"
        }


@measure_execution_time
def check_text_to_html_ratio(soup, results):
    """
    Checks text-to-HTML ratio
    """
    text = soup.get_text(separator=' ', strip=True)
    html_length = len(str(soup))
    text_length = len(text)

    if html_length == 0:
        ratio = 0
    else:
        ratio = text_length / html_length

    results["results"]["content"]["text_to_html_ratio"] = {
        "value": round(ratio, 2),
        "status": "Good" if ratio > 0.15 else "Needs Improvement",
        "rating": 9 if ratio > 0.15 else 5,
        "reason": f"Text-to-HTML ratio: {ratio:.2f}",
        "category":"Average Priority",
    }

@measure_execution_time
def check_iframe_usage(soup, results):
    """
    Checks for excessive iframe usage.
    """
    iframes = soup.find_all("iframe")
    iframe_count = len(iframes)

    results["results"]["content"]["iframe_usage"] = {
        "value": iframe_count,
        "status": "Good" if iframe_count <= 3 else "Needs Improvement",
        "rating": 9 if iframe_count <= 3 else 5,
        "reason": f"Number of iframes: {iframe_count}",
         "category":"Low Priority",
    }

@measure_execution_time
def check_flash_usage(soup, results):
    flash_count = sum(1 for tag in soup.find_all(["embed", "object"]) 
                    if tag.get("type") == "application/x-shockwave-flash")

    results["results"]["content"]["flash_usage"] = {
        "value": flash_count,
        "status": "Poor" if flash_count > 0 else "Good",
        "rating": 1 if flash_count > 0 else 10,
        "reason": f"{flash_count} Flash elements found",
        "category":"Low Priority",
    }


@measure_execution_time
async def check_broken_resource_link(soup, base_url, results):
    """Asynchronously checks for broken resource links (images, CSS, JS files)."""
    async def fetch_head(session, base_url):
        """Helper function to send an async HEAD request."""
        try:
            async with session.head(base_url, timeout=5) as response:
                return base_url, response.status
        except aiohttp.ClientError:
            return base_url, None  # Return None if request fails

    resources = soup.find_all(["img", "link", "script"])
    broken_links = []
    
    async with aiohttp.ClientSession() as session:
        tasks = []
        for resource in resources:
            resource_url = resource.get("src") if resource.name in ["img", "script"] else resource.get("href")
            if resource_url:
                absolute_url = urljoin(base_url, resource_url)
                tasks.append(fetch_head(session, absolute_url))
        
        responses = await asyncio.gather(*tasks)  # Execute all requests concurrently

        # Check responses for broken links
        broken_links = [res_url for res_url, status in responses if status is None or status >= 400]

    # Store results in the 'results' dictionary
    results["results"]["content"]["broken_resource_links"] = {
        "value": len(broken_links),
        "status": "Needs Improvement" if broken_links else "Good",
        "rating": 4 if broken_links else 10,
        "reason": f"Found {len(broken_links)} broken resource links" if broken_links else "No broken resource links found",
        "category":"Average Priority",
    }

@measure_execution_time
def check_content_has_lists(soup, results):
    # Checks if content uses lists (ul, ol).  
    ul_lists = soup.find_all("ul")
    ol_lists = soup.find_all("ol")
    list_count = len(ul_lists) + len(ol_lists)

    results["results"]["content"]["content_has_lists"] = {
        "value": list_count > 0,
        "status": "Good" if list_count > 0 else "Needs Improvement",
        "rating": 9 if list_count > 0 else 5,
        "reason": f"Lists found: {list_count}",
        "category":"Average Priority",
    }


@measure_execution_time
def check_content_has_tables(soup, results):
    
    # Checks if content uses tables.
    tables = soup.find_all("table")
    table_count = len(tables)
    results["results"]["content"]["content_has_tables"] = {
        "value": table_count > 0,
        "status": "Good" if table_count > 0 else "Needs Improvement",
        "rating": 9 if table_count > 0 else 5,
        "reason": f"Tables found: {table_count}",
        "category":"Average Priority",
    }

@measure_execution_time
def check_responsive_design(soup, results):
    viewport_meta = soup.find("meta", attrs={"name": "viewport"})
    content = viewport_meta.get("content", "") if viewport_meta else ""
    is_responsive = "width=device-width" in content

    results["results"]["mobile"]["responsive_design"] = {
        "value": content if is_responsive else False,  # Changed to show actual content
        "status": "Good" if is_responsive else "Needs Improvement",
        "rating": 9 if is_responsive else 5,
        "reason": "Viewport meta tag indicates responsiveness" 
                if is_responsive 
                else "Viewport meta tag missing or not properly configured",
        "category":"High Priority",
    }


@measure_execution_time
def check_dublicate_title_tags(soup, results):
    title_text = soup.title.string.strip() if soup.title and soup.title.string else ""

    is_duplicate = title_text in results["results"]["meta_tags"]
    
    # Instead of update(), assign the dictionary directly
    results["results"]["meta_tags"]["duplicate_title_tags"] = {
        "value": is_duplicate,
        "status": "Needs Improvement" if is_duplicate else "Good",
        "rating": 5 if is_duplicate else 9,
        "reason": "Duplicate title tag found" if is_duplicate else "Title tag is unique",
        "category":"Low Priority",
    }


@measure_execution_time
def check_page_load_time(response, results,base_url):
    """
    Checks the page load time based on the response object.
    Updates the 'results' dictionary with the load time and status.
    """
    try:
        response = requests.get(base_url)
        # Calculate load time
        load_time = round(response.elapsed.total_seconds(), 2)

        if response.elapsed is None:
            print("response.elapsed is None (Page load time could not be measured)")
        else:
            print(f"Page load time: {response.elapsed.total_seconds()} seconds")
                    # Determine status and rating based on load time
        if load_time <= 3:
            status, rating = "Good", 10
        elif load_time <= 10:
            status, rating = "Needs Improvement", 5
        else:
            status, rating = "Poor", 1

        # Update results
        results["results"]["performance"]["page_load_time"] = {
            "value": load_time,
            "status": status,
            "rating": rating,
            "reason": f"Page load time: {load_time} seconds",
            "category":"High Priority",
        }

    except Exception as e:
        # Update results with error information
        results["results"]["performance"]["page_load_time"] = {
            "value": None,
            "status": "Error",
            "rating": 1,
            "reason": f"Failed to measure load time: {str(e)}",
            "category":"High Priority",
        }


@measure_execution_time
def check_duplicate_content(soup, results):
    content_hashes = set()  # Store hashes of previously processed content

    # Extract main content: text, image sources, and anchor links
    content = ''.join([
        soup.get_text(separator=" ", strip=True),
        *[img["src"] for img in soup.find_all("img") if img.get("src")],
        *[a["href"] for a in soup.find_all("a") if a.get("href")]
    ])

    # Generate MD5 hash of the content
    content_hash = md5(content.encode()).hexdigest()

    # Check for duplicate content
    is_duplicate = content_hash in content_hashes
    status = "Needs improvement" if is_duplicate else "Good"
    rating = 5 if is_duplicate else 9
    reason = "Duplicate content detected" if is_duplicate else "Content is unique"

    # Update results dictionary
    results["results"]["content"]["duplicate_content"] = {
        "value": is_duplicate,
        "rating": rating,
        "status": status,
        "reason": reason,
         "category":"High Priority",
    }

    # Track hash for future comparisons
    if not is_duplicate:
        content_hashes.add(content_hash)

@measure_execution_time
def check_heading_structure(soup, results):
    headings = soup.find_all(re.compile("^h[1-6]$"))

    # Initialize results storage
    results["results"]["headings"]["heading_structure"] = {}

    if not headings:
        results["results"]["headings"]["heading_structure"] = {
            "value": "No headings found",
            "status": "Needs Improvement",
            "rating": 3,
            "reason": "No heading tags found on the page.",
            "suggestion": "Use headings (H1-H6) to structure your content properly.",
            "category":"High Priority",
        }
        return
    
    last_level = 0
    skipped_levels = []
    found_headings = []  # Stores found heading levels

    for heading in headings:
        level = int(heading.name[1])  # Extract heading level (e.g., "h2" -> 2)
        found_headings.append(f"H{level}")  # Store for logging

        if last_level and level > last_level + 1:
            skipped_levels.append(f"H{last_level} to H{level}")  # Log skipped levels
        
        last_level = level

    # Check if H1 is missing
    has_h1 = any(h.name == "h1" for h in headings)

    if not has_h1:
        results["results"]["headings"]["heading_structure"]["missing_h1"] = {
            "value": "H1 is missing",
            "status": "Needs Improvement",
            "rating": 4,
            "reason": "No H1 tag found, which is important for SEO.",
            "suggestion": "Add an H1 tag to define the main topic of the page.",
            "category":"High Priority",
        }

    if skipped_levels:
        results["results"]["headings"]["heading_structure"]={
            "value": f"Skipped levels: {', '.join(skipped_levels)}",
            "status": "Needs Improvement",
            "rating": 3,
            "reason": f"Heading levels skipped: {', '.join(skipped_levels)}",
            "suggestion": "Use sequential heading levels (e.g., H1 → H2 → H3) for better structure.",
            "category":"High Priority",
        }
    else:
        results["results"]["headings"]["heading_structure"]={
            "value": "Correct heading structure",
            "status": "Good",
            "rating": 9,
            "reason": "Headings are in correct order.",
            "found_headings": found_headings,  # Logs which headings exist
            "category":"High Priority",
        }

def evaluate_seo_rules(soup, base_url, target_keyword=None):
    """"Evaluates SEO rules for a given URL and returns a structured report."""
    results = {
        # "url": url,
        "results": defaultdict(dict),
        "seo_final_rating": 0,
        "errors": {},

    }
    response = None  # Initialize response to none.

    try:
        logger.info(f"Evaluating SEO rules for URL: {base_url}")
        if soup is None:       #If soup is None, the function fetches the webpage again using requests.get()
            logger.info(f"Fetching URL: {base_url}")
            response = requests.get(base_url, timeout=10)
            logger.info(f"Response status code: {response.status_code}")
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
    except Exception as e:
        results["errors"]["base"] = str(e)
        return results     #error message is stored on result

    if not isinstance(soup, BeautifulSoup):
        results["errors"]["base"] = "Invalid or missing HTML content"
        return results       


    # Execute all checks
    seo_checks=[
        (check_meta_tags, (soup, results)),
        (check_meta_keywords_tag,(soup,results)),
        (check_headings, (soup, results)),
        (check_content, (soup, results)),
        (check_technical, (soup, results, base_url)),
        (check_security, (soup, results, base_url)),
        (check_url, (soup, results,base_url)),
        (check_mobile, (soup, results)),
        (check_schema, (soup, results)),
        (check_links, (soup, results,base_url)),
        (check_responsive_design, (soup, results)),
        (check_canonical_tag_valid, (soup, results, base_url)),
        (check_robots_meta_tag_exists, (soup, results)),
        (check_noindex_tag_check, (soup, results)),
        (check_nofollow_tag_check, (soup, results)),
        (check_image_file_size_optimized, (soup, results, base_url)),
        (check_image_dimensions_specified, (soup, results)),
        (check_broken_internal_links, (soup, results,base_url)),
        (check_broken_external_links, (soup, results, base_url)),
        (check_nofollow_on_external_links, (soup, results)),
        (check_gzip_compression,(base_url, results,response)),
        (check_browser_caching_enabled, (response, results,base_url)),
        (check_redirects_minimized, (base_url, results)),
        (check_xml_sitemap_exists, (base_url, results)),
        (check_keyword_in_title, (soup, results, target_keyword)),
        (check_keyword_in_h1, (soup, results, target_keyword)),
        (check_keyword_density, (soup, results, target_keyword)),
        (check_content_freshness, (base_url, soup, results)),
        (check_https_redirect, (base_url, results)),
        (check_internal_linking_depth, (soup, results)),
        (check_external_linking_quality,(soup, results, base_url)),
        (check_dublicate_title_tags, (soup, results)),
        (check_duplicate_content, (soup, results)),
        (check_page_depth, (base_url, results)),
        (check_content_readability, (soup, results)),
        (check_social_meta_tags, (soup, results)),
        (check_favicon_exists, (soup, base_url, results)),
        (check_text_to_html_ratio, (soup, results)),
        (check_iframe_usage, (soup, results)),
        (check_flash_usage, (soup, results)),
        (check_broken_resource_link, (soup, base_url, results)),
        (check_content_has_lists, (soup, results)),
        (check_content_has_tables, (soup, results)),
        (check_page_load_time, (response, results,base_url)),
        (check_heading_structure, (soup, results)),
    ]

    sync_checks = []
    async_checks = []

    for func, args in seo_checks:
        if asyncio.iscoroutinefunction(func):
            async_checks.append((func, args))
        else:
            sync_checks.append((func, args))

#execute seo_check in parallel
    with ThreadPoolExecutor(max_workers=4) as executor:
        logger.info("Executing synchronous checks in parallel...")
        future_to_check={executor.submit(func, *args):func for func, args in sync_checks}

        for future in as_completed(future_to_check):
            logger.info(f"Check {future_to_check[future].__name__} completed.")
            try:
                future.result()
            except Exception as e:
                logger.error(f"Error in check {future_to_check[future].__name__}: {str(e)}")
                check_name=future_to_check[future].__name__
                logger.error(f"Error in {check_name}: {e}")
                results["errors"][check_name]=str(e)   # store error per check

     # Execute async checks
    async def run_async_checks(async_checks):
        async_tasks = [func(*args) for func, args in async_checks]
        await asyncio.gather(*async_tasks)

    if async_checks:
        asyncio.run(run_async_checks(async_checks))


    # Calculate overall rating
    total = 0
    count = 0
    for category in results["results"].values():
        for rule in category.values():
            if rule["rating"] > 0:
                total += rule["rating"]
                count += 1
    
    total_rules = sum(len(category) for category in results["results"].values())
     # Finalize and return results           
    results["seo_final_rating"] = round(total / count, 2) if count else 0
    results["Total_rules"]=total_rules
    

    # Add this function to filter issues with rating < 5
    def filter_issues(results):
        """
        Filters issues with a rating less than 5 and organizes them into an 'Issues' section.
        """
        issues = []

        # Recursive function to traverse nested dictionaries
        def traverse(d):
            if isinstance(d, dict):
                for key, value in d.items():
                    if isinstance(value, dict):
                        # Check if the current dictionary has a "rating" key
                        if "rating" in value and value["rating"] < 3:
                            issues.append({
                                "key": key,
                                "value": value.get("value"),
                                "status": value.get("status"),
                                "rating": value.get("rating"),
                                "reason": value.get("reason"),
                                "category":value.get("category")
                            })
                        # Recurse into nested dictionaries
                        traverse(value)

        # Start traversing from the root of the results
        traverse(results)

        return {
            "count": len(issues),
            "issues": issues
        }
    results["Issues"] = filter_issues(results)
    

    return dict(results)



