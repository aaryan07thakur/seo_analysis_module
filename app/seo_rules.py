import requests
from bs4 import BeautifulSoup, Tag
from urllib.parse import urljoin, urlparse
import re
# from difflib import SequenceMatcher
from collections import defaultdict
from datetime import datetime
from collections import Counter #for keyword density
from readability.readability import Document
from lxml import html
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from hashlib import md5
import asyncio
import aiohttp
from dateutil import parser
from functools import wraps

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



SEO_RULES = [
    {"name": "title_tag_exists", "description": "Check if <title> tag exists", "priority" : "critical"},
    {"name": "title_tag_length", "description": "Check if title tag length is within 50-60 characters"},
    {"name": "h1_tag_exists", "description": "Check if <h1> tag exists"},
    {"name": "h1_tag_unique", "description": "Check if <h1> tag is unique on the page"},
    {"name": "h2_tags_exist", "description": "Check if <h2> tags exist"},
    {"name": "h3_tags_exist", "description": "Check if <h3> tags exist"},
    {"name": "alt_attributes_exist", "description": "Check if all images have alt attributes"},
    {"name": "alt_attributes_descriptive", "description": "Check if alt attributes are descriptive"},
    {"name": "page_load_time", "description": "Check if page load time is under 3 seconds"},
    {"name": "responsive_design", "description": "Check if the page is mobile-friendly"},
    {"name": "canonical_tag_exists", "description": "Check if canonical tag exists"},
    {"name": "canonical_tag_valid", "description": "Check if canonical tag points to a valid URL"},
    {"name": "robots_meta_tag_exists", "description": "Check if robots meta tag exists"},
    {"name": "noindex_tag_check", "description": "Check if the page is marked as noindex"},
    {"name": "nofollow_tag_check", "description": "Check if the page is marked as nofollow"},
    {"name": "image_file_size_optimized", "description": "Check if image file sizes are optimized"},
    {"name": "image_dimensions_specified", "description": "Check if image dimensions are specified"},
    {"name": "internal_links_exist", "description": "Check if internal links exist on the page"},
    {"name": "external_links_exist", "description": "Check if external links exist on the page"},
    {"name": "broken_internal_links", "description": "Check for broken internal links"},
    {"name": "broken_external_links", "description": "Check for broken external links"},
    {"name": "nofollow_on_external_links", "description": "Check if external links have rel='nofollow'"},
    {"name": "gzip_compression_enabled", "description": "Check if GZIP compression is enabled"},
    {"name": "browser_caching_enabled", "description": "Check if browser caching is enabled"},
    {"name": "ssl_certificate_installed", "description": "Check if SSL certificate is installed"},
    {"name": "redirects_minimized", "description": "Check if redirects are minimized (avoid chains)"},
    {"name": "xml_sitemap_exists", "description": "Check if XML sitemap exists"},
    {"name": "robots_txt_exists", "description": "Check if robots.txt file exists"},
    {"name": "url_length_optimized", "description": "Check if url length is optimized"},
    {"name": "url_keywords", "description": "Check if url contains keywords"},
    {"name": "meta_description_exists", "description": "Check if meta description exists"},
    {"name": "meta_description_length", "description": "Check if meta description length is within 150-160 characters"},
    {"name": "schema_markup_exists", "description": "Check if schema markup exists"},
    {"name": "content_length", "description": "Check if content length is sufficient"},
    {"name": "keyword_in_title", "description": "Check if target keyword is in title"},
    {"name": "keyword_in_h1", "description": "Check if target keyword is in h1"},
    {"name": "keyword_density", "description": "Check keyword density"},
    {"name": "content_freshness", "description": "Check for recent content updates"},
    {"name": "core_web_vitals_lcp", "description": "Check LCP Core web vital"},
    {"name": "core_web_vitals_fid", "description": "Check FID Core web vital"},
    {"name": "core_web_vitals_cls", "description": "Check CLS Core web vital"},
    {"name": "https_redirect", "description": "Check if http redirects to https"},
    {"name": "mobile_viewport", "description": "Check if viewport is configured for mobile"},
    {"name": "structured_data_valid", "description": "Check for structured data validity"},
    {"name": "internal_linking_depth", "description": "Check internal linking depth"},
    {"name": "external_linking_quality", "description": "Check external linking quality"},
    {"name": "duplicate_content", "description": "Check for duplicate content"},
    {"name": "page_depth", "description": "Check page depth from homepage"},
    {"name": "content_readability", "description": "Check content readability"},
    {"name": "social_meta_tags", "description": "Check social meta tags (og:, twitter:)"},
    {"name": "favicon_exists", "description": "Check if favicon exists"},
    {"name": "text_to_html_ratio", "description": "Check text to html ratio"},
    {"name": "iframe_usage", "description": "Check excessive iframe usage"},
    {"name": "flash_usage", "description": "Check flash usage"},
    {"name": "html_validation", "description": "Check for html validation errors"},
    {"name": "css_validation", "description": "Check for css validation errors"},
    {"name": "javascript_errors", "description": "Check for javascript errors"},
    {"name": "broken_resource_links", "description": "Check for broken resource links(css, js)"},
    {"name": "content_has_lists", "description": "Check if content uses lists"},
    {"name": "content_has_tables", "description": "Check if content uses tables"},
    {"name": "content_has_videos", "description": "Check if content has videos"},
]

def evaluate_seo_rules(soup, url, target_keyword=None):
    results = {
        "url": url,
        "results": defaultdict(dict),
        "seo_rating": 0,
        "errors": {}
    }
    response = None  # Initialize response to none.

    try:
        if soup is None:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
    except Exception as e:
        results["errors"]["base"] = str(e)
        return results

    if not isinstance(soup, BeautifulSoup):
        results["errors"]["base"] = "Invalid or missing HTML content"
        return results

    # Meta Tags Evaluation
    @measure_execution_time
    def check_meta_tags(soup, results):
        title_tag = soup.title
        title_text = title_tag.string.strip() if title_tag and title_tag.string else ""
        # Define title_len BEFORE it's used:
        title_len = len(title_text)
        # Handle None explicitly if needed:
        title_value = title_tag.string if title_tag and title_tag.string else "Missing Title" if title_tag is None else None


    #Title tag_exists
        title_exists_status="Good" if title_tag else "poor"
        title_exists_rating=10 if title_tag else 1
        title_extsts_reasons="Title_tag_Present" if title_tag else "Missing Title_tags-critical for SEO"

        results["results"]["meta_tags"]["title_tag_exists"] = {
            "value": title_value,
            "status": title_exists_status,
            "rating": title_exists_rating,
            "reason": title_extsts_reasons
        }
    #Title_tag length
        title_length_status="Good" if 50<=title_len <=60 else "Needs Improvement"
        title_length_rating=10 if 50<=title_len <=60 else 5
        title_length_reasons="Optimal length (50-60 chars)" if 50 <= title_len <= 60 else f"Title length: {title_len} chars (should be 50-60)"

        results["results"]["meta_tags"]["title_tag_length"] = {
            "value": title_len,
            "status": title_length_status,
            "rating": title_length_rating,
            "reason": title_length_reasons
        }

    meta_description = soup.find("meta", attrs={"name": "description"})
    desc_content = ""
    if isinstance(meta_description, Tag):
        content = meta_description.get("content")
        if isinstance(content, str):
            desc_content = content.strip()

# Meta description exists
    desc_exists_value=str(meta_description) if meta_description else False
    desc_exists_status="Good" if meta_description else "poor"
    desc_exists_rating=10 if meta_description else 1
    desc_exists_reason="Meta description present" if meta_description else "Missing meta description"

    
    results["results"]["meta_tags"]["meta_description_exists"] = {
        "value": desc_exists_value,
        "status": desc_exists_status,
        "rating": desc_exists_rating,
        "reason": desc_exists_reason
    }

    #meta_description length 
    decs_length_status="Good" if 150 <= len(desc_content) <= 160 else "Needs Improvement"
    decs_length_rating=9 if 150 <= len(desc_content) <= 160 else 5
    decs_length_reasons="Optimal length (150-160 chars)" if 150 <= len(desc_content) <= 160 else f"Length: {len(desc_content)} chars (should be 150-160)"
    
    results["results"]["meta_tags"]["meta_description_length"] = {
        "value": len(desc_content),
        "status": decs_length_status,
        "rating": decs_length_rating,
        "reason": decs_length_reasons
    }

    # Headings Evaluation
    @measure_execution_time
    def check_headings(soup, results):
        h1_tags = soup.find_all("h1")
        h2_tags = soup.find_all("h2")
        h3_tags = soup.find_all("h3")
        
        results["results"]["headings"]["h1_tag_exists"] = {
            "value": len(h1_tags) > 0,
            "status": "Good" if len(h1_tags) > 0 else "Poor",
            "rating": 10 if len(h1_tags) > 0 else 1,
            "reason": "H1 tag found" if len(h1_tags) > 0 else "Missing H1 tag"
        }
        
        results["results"]["headings"]["h1_tag_unique"] = {
            "value": True if len(h1_tags) == 1 else (False if len(h1_tags) == 0 else len(h1_tags)),
            "status": "Good" if len(h1_tags) == 1 else "Poor",
            "rating": 10 if len(h1_tags) == 1 else (5 if len(h1_tags) > 1 else 1),
            "reason": "H1 tag is unique" if len(h1_tags) == 1 else 
                    ("There is no H1 tag found" if len(h1_tags) == 0 else "There is not a unique H1 tag")
        }
        
        results["results"]["headings"]["h2_tags_exist"] = {
            "value": len(h2_tags) > 0,
            "status": "Good" if len(h2_tags) > 0 else "Needs Improvement",
            "rating": 9 if len(h2_tags) > 0 else 5,
            "reason": f"{len(h2_tags)} H2 tags found" if len(h2_tags) > 0 else "No H2 tags"
        }
        
        results["results"]["headings"]["h3_tags_exist"] = {
            "value": len(h3_tags) > 0,
            "status": "Good" if len(h3_tags) > 0 else "Needs Improvement",
            "rating": 8 if len(h3_tags) > 0 else 5,
            "reason": f"{len(h3_tags)} H3 tags found" if len(h3_tags) > 0 else "No H3 tags"
        }

    # Content Evaluation
    @measure_execution_time
    def check_content(soup, results):
        # Alt Attributes
        images = soup.find_all("img")
        alt_exists = all(img.get("alt") for img in images)
        results["results"]["content"]["alt_attributes_exist"] = {
            "value": alt_exists,
            "status": "Good" if alt_exists else "Needs Improvement",
            "rating": 9 if alt_exists else 5,
            "reason": "All images have alt attributes" if alt_exists else "Missing alt attributes"
        }
        
        # Descriptive Alt Text
        if alt_exists:
            descriptive = all(len(img["alt"].split()) > 3 for img in images if img.get("alt"))
            results["results"]["content"]["alt_attributes_descriptive"] = {
                "value": descriptive,
                "status": "Good" if descriptive else "Needs Improvement",
                "rating": 8 if descriptive else 5,
                "reason": "Alt texts are descriptive" if descriptive else "Some alt texts too generic"
            }

        # Content Length
        word_count = len(soup.get_text().split())
        results["results"]["content"]["content_length"] = {
            "value": word_count,
            "status": "Good" if word_count >= 500 else "Needs Improvement",
            "rating": 10 if word_count >= 1000 else 8 if word_count >= 500 else 5,
            "reason": f"{word_count} words (good)" if word_count >= 500 else "Content too short"
        }

    # Technical SEO
    @measure_execution_time
    def check_technical(soup, results):
        # Canonical Tag
        canonical = soup.find("link", rel="canonical")
        results["results"]["technical"]["canonical_tag_exists"] = {
            "value": bool(canonical),
            "status": "Good" if canonical else "Needs Improvement",
            "rating": 8 if canonical else 5,
            "reason": "Canonical tag present" if canonical else "Missing canonical tag"
        }
        
        # Robots.txt
        robots_url = f"{url.rstrip('/')}/robots.txt"
        try:
            robots_resp = requests.get(robots_url, timeout=5)
            results["results"]["technical"]["robots_txt_exists"] = {
                "value": robots_resp.status_code == 200,
                "status": "Good" if robots_resp.status_code == 200 else "Needs Improvement",
                "rating": 9 if robots_resp.status_code == 200 else 5,
                "reason": "robots.txt found" if robots_resp.status_code == 200 else "Missing robots.txt"
            }
        except:
            results["results"]["technical"]["robots_txt_exists"] = {
                "value": False,
                "status": "Error",
                "rating": 1,
                "reason": "Failed to check robots.txt"
            }

    # Performance
    @measure_execution_time
    async def check_performance(soup, results, response=None):
        if response:
            await asyncio.gather(
                check_page_load_time(response, results),
                check_gzip_compression_enabled(response, results),
                check_browser_caching_enabled(response, results)
            )
        else:
            results["results"]["performance"]["page_load_time"] = {
                "value": None,
                "status": "Error",
                "rating": 1,
                "reason": "Failed to measure load time, no response object"
            }
            results["results"]["performance"]["gzip_compression_enabled"] = {
                "value": None,
                "status": "Error",
                "rating": 1,
                "reason": "Failed to check gzip, no response object"
            }
            results["results"]["performance"]["browser_caching_enabled"] = {
                "value": None,
                "status": "Error",
                "rating": 1,
                "reason": "Failed to check caching, no response object"
            }

    # Security
    @measure_execution_time
    def check_security(soup, results):
        # SSL Certificate
        ssl_status = url.startswith("https")
        results["results"]["security"]["ssl_certificate_installed"] = {
            "value": ssl_status,
            "status": "Good" if ssl_status else "Needs Improvement",
            "rating": 10 if ssl_status else 5,
            "reason": "HTTPS enabled" if ssl_status else "Using insecure HTTP"
        }

    # URL Structure
    @measure_execution_time
    def check_url(soup, results):
        parsed = urlparse(url)
        path_len = len(parsed.path)
        results["results"]["url"]["url_length_optimized"] = {
            "value": path_len <= 75,
            "status": "Good" if path_len <= 75 else "Needs Improvement",
            "rating": 9 if path_len <= 75 else 5,
            "reason": f"URL length: {path_len} chars" if path_len <= 75 else "URL too long"
        }
        
        keyword_in_url = target_keyword and target_keyword in parsed.path.lower()
        results["results"]["url"]["url_keywords"] = {
            "value": keyword_in_url,
            "status": "Good" if keyword_in_url else "Needs Improvement",
            "rating": 10 if keyword_in_url else 5,
            "reason": "Keyword in URL" if keyword_in_url else "Missing keyword in URL"
        }

    # Mobile Optimization
    @measure_execution_time
    def check_mobile(soup, results):
        viewport = soup.find("meta", attrs={"name": "viewport"})
        results["results"]["mobile"]["mobile_viewport"] = {
            "value": bool(viewport),
            "status": "Good" if viewport else "Needs Improvement",
            "rating": 10 if viewport else 5,
            "reason": "Mobile viewport configured" if viewport else "Missing viewport meta tag"
        }

    # Schema Markup
    @measure_execution_time
    def check_schema(soup, results):
        schema_tags = soup.find_all("script", type="application/ld+json")
        results["results"]["schema"]["schema_markup_exists"] = {
            "value": len(schema_tags) > 0,
            "status": "Good" if len(schema_tags) > 0 else "Needs Improvement",
            "rating": 8 if len(schema_tags) > 0 else 5,
            "reason": f"{len(schema_tags)} schema tags found" if schema_tags else "No schema markup"
        }

    # Link Analysis
    @measure_execution_time
    def check_links(soup, results):
        internal_links = [a for a in soup.find_all("a") if not a.get("href", "").startswith("http")]
        external_links = [a for a in soup.find_all("a") if a.get("href", "").startswith("http")]
        
        # Internal Links
        results["results"]["links"]["internal_links_exist"] = {
            "value": len(internal_links) > 0,
            "status": "Good" if len(internal_links) > 0 else "Needs Improvement",
            "rating": 9 if len(internal_links) > 0 else 5,
            "reason": f"{len(internal_links)} internal links found" if internal_links else "No internal links"
        }
        
        # External Links
        results["results"]["links"]["external_links_exist"] = {
            "value": len(external_links) > 0,
            "status": "Good" if len(external_links) > 0 else "Needs Improvement",
            "rating": 8 if len(external_links) > 0 else 5,
            "reason": f"{len(external_links)} external links found" if external_links else "No external links"
        }

    # Validation Checks
    # def check_validation(soup, results):
    #     html_errors = "Not implemented - requires W3C API"
    #     results["results"]["validation"]["html_validation"] = {
    #         "value": html_errors,
    #         "status": "Not Implemented",
    #         "rating": 0,
    #         "reason": "HTML validation requires external tools"
    #     }


    @measure_execution_time
    def check_canonical_tag_valid(soup, results, url):
        canonical = soup.find("link", rel="canonical")
        if canonical and canonical.get("href"):
            canonical_url = urljoin(url, canonical["href"]).split("?")[0].split("#")[0] #remove query parameters and fragments.
            current_url = url.split("?")[0].split("#")[0]
            if canonical_url == current_url:
                results["results"]["technical"]["canonical_tag_valid"] = {
                    "value": True,
                    "status": "Good",
                    "rating": 10,
                    "reason": "Canonical URL points to the correct page",
                }
            else:
                results["results"]["technical"]["canonical_tag_valid"] = {
                    "value": False,
                    "status": "Needs Improvement",
                    "rating": 5,
                    "reason": f"Canonical URL ({canonical_url}) does not match current URL ({current_url})",
                }
        else:
            results["results"]["technical"]["canonical_tag_valid"] = {
                "value": False,
                "status": "Needs Improvement",
                "rating": 5,
                "reason": "No canonical tag found",
            }



    @measure_execution_time
    def check_robots_meta_tag_exists(soup, results):
        robots_meta = soup.find("meta", attrs={"name": "robots"})
        robots_meta_value =  robots_meta["content"] if robots_meta else False
        results["results"]["technical"]["robots_meta_tag_exists"] = {
            "value": robots_meta_value,
            "status": "Good" if robots_meta else "Needs Improvement",
            "rating": 8 if robots_meta else 5,
            "reason": "Robots meta tag present" if robots_meta else "Missing robots meta tag",
        }


    @measure_execution_time
    def check_noindex_tag_check(soup, results):
        robots_meta = soup.find("meta", attrs={"name": "robots"})
        noindex = robots_meta and "noindex" in robots_meta.get("content", "").lower()
        results["results"]["technical"]["noindex_tag_check"] = {"value": noindex, "status": "Needs Improvement" if noindex else "Good", "rating": 1 if noindex else 10, "reason": "Page is noindex" if noindex else "Page is indexable"}


    @measure_execution_time
    def check_nofollow_tag_check(soup, results):
        robots_meta = soup.find("meta", attrs={"name": "robots"})
        nofollow = robots_meta and "nofollow" in robots_meta.get("content", "").lower()
        results["results"]["technical"]["nofollow_tag_check"] = {"value": nofollow, "status": "Needs Improvement" if nofollow else "Good", "rating": 1 if nofollow else 10, "reason": "Page is nofollow" if nofollow else "Links are followed"}

    
    @measure_execution_time
    def check_image_dimensions_specified(soup, results):
        images = soup.find_all("img")
        missing_dims = any(not img.get("width") or not img.get("height") for img in images)
        results["results"]["content"]["image_dimensions_specified"] = {
            "value": not missing_dims, 
            "status": "Good" if not missing_dims else "Needs Improvement", 
            "rating": 8 if not missing_dims else 5, 
            "reason": "Image dimensions specified" if not missing_dims else "Missing image dimensions"}


    @measure_execution_time
    def check_nofollow_on_external_links(soup, results):
        external_links = [a for a in soup.find_all("a") if a.get("href", "").startswith("http")]
        nofollow_links = [link for link in external_links if link.get("rel") and "nofollow" in link.get("rel")]
        results["results"]["links"]["nofollow_on_external_links"] = {"value": len(nofollow_links), "status": "Good", "rating": 8, "reason": f"{len(nofollow_links)} external links have nofollow"}


    @measure_execution_time
    async def check_gzip_compression_enabled(response, results):
        await asyncio.sleep(0)  # Simulating async behavior
        # Add gzip checking logic here
        results["results"]["performance"]["gzip_compression_enabled"] = {
            "value": True,  # Replace with actual check
            "status": "Good",
            "rating": 10,
            "reason": "Gzip compression is enabled"
        }


    @measure_execution_time
    async def check_browser_caching_enabled(response, results):
        await asyncio.sleep(0)  # Simulating async behavior
        # Add caching check logic here
        results["results"]["performance"]["browser_caching_enabled"] = {
            "value": True,  # Replace with actual check
            "status": "Good",
            "rating": 10,
            "reason": "Browser caching is enabled"
        }

   
    @measure_execution_time
    def check_xml_sitemap_exists(url, results):
        sitemap_url = urljoin(url, "sitemap.xml")
        try:
            requests.get(sitemap_url, timeout=5)
            results["results"]["technical"]["xml_sitemap_exists"] = {"value": True, "status": "Good", "rating": 9, "reason": "XML sitemap found"}
        except:
            results["results"]["technical"]["xml_sitemap_exists"] = {
                "value": False, 
                "status": "Needs Improvement", 
                "rating": 5, 
                "reason": "XML sitemap missing"}


    @measure_execution_time
    def check_keyword_in_title(soup, results, target_keyword):
        title_tag = soup.title
        title_text = title_tag.string.lower() if title_tag and title_tag.string else ""
        keyword_in_title = target_keyword and target_keyword.lower() in title_text
        results["results"]["content"]["keyword_in_title"] = {"value": keyword_in_title, "status": "Good" if keyword_in_title else "Needs Improvement", "rating": 10 if keyword_in_title else 5, "reason": "Keyword in title" if keyword_in_title else "Keyword not in title"}


    @measure_execution_time
    def check_keyword_in_h1(soup, results, target_keyword):
        h1_tags = soup.find_all("h1")
        h1_text = " ".join(tag.get_text().lower() for tag in h1_tags)
        keyword_in_h1 = target_keyword and target_keyword.lower() in h1_text
        results["results"]["content"]["keyword_in_h1"] = {"value": keyword_in_h1, "status": "Good" if keyword_in_h1 else "Needs Improvement", "rating": 10 if keyword_in_h1 else 5, "reason": "Keyword in H1" if keyword_in_h1 else "Keyword not in H1"}


    @measure_execution_time
    def check_image_file_size_optimized(soup, results, url):
        images = soup.find_all("img")
        all_optimized = True  # Assume all images are optimized unless proven otherwise

        for img in images:
            img_url = urljoin(url, img.get("src"))  # Fix typo from `gate` to `get`
            try:
                response = requests.head(img_url, timeout=5)  # Fix inconsistent variable name
                filesize = int(response.headers.get("Content-Length", 0)) / 1024  # Convert bytes to KB

                if filesize > 150:
                    results["results"]["content"]["image_file_size_optimized"] = {
                        "value": "False",  # Fix typo "Flase" to "False"
                        "status": "Needs Improvement",
                        "rating": 5,
                        "reason": f'Image {img_url} is too large ({filesize:.2f} KB)'
                    }
                    all_optimized = False  # Mark that at least one image is too large

            except Exception as e:
                results["results"]["content"]["image_file_size_optimized"] = {
                    "value": "Error",
                    "status": "Error",
                    "rating": 1,  # Fix: Ensure rating is an integer
                    "reason": f'Failed to check size of image {img_url}. Error: {str(e)}'
                }
                return  # Exit function if there's an error

        if all_optimized:  # If no large images were found
            results["results"]["content"]["image_file_size_optimized"] = {
                "value": "True",
                "status": "Good",
                "rating": 9,
                "reasons": "All images are optimized"
            }
 

    @measure_execution_time
    def check_broken_internal_links(soup, results):
        internal_links = [urljoin(url, a.get("href")) for a in soup.find_all("a", href=True) if a.get("href").startswith(("/", "./"))]
        broken_links = []

        for link in internal_links:
            try:
                response = requests.head(link, timeout=5)
                if response.status_code >= 400:
                    broken_links.append(f"{link} ({response.status_code})")
            except Exception as e:
                broken_links.append(f"{link} (Error: {str(e)})")

        if broken_links:
            results["results"]["links"]["broken_internal_links"] = {
                "value": False,
                "status": "Needs Improvement",
                "rating": 1,
                "reason": f"Broken internal links found: {', '.join(broken_links)}"
            }
        else:
            results["results"]["links"]["broken_internal_links"] = {
                "value": True,
                "status": "Good",
                "rating": 9,
                "reason": "No broken internal links found"
            }
    

    @measure_execution_time
    def check_broken_external_links(soup, results, url):
        external_links = [
            a.get("href") for a in soup.find_all("a", href=True)
            if a.get("href").startswith("http") and urlparse(a.get("href")).netloc != urlparse(url).netloc
        ]
        broken_links = []

        def check_link(link):
            try:
                response = requests.head(link, timeout=5)
                if response.status_code >= 400:
                    return f"{link} ({response.status_code})"
            except Exception as e:
                return f"{link} (Error: {str(e)})"
            return None

        with ThreadPoolExecutor(max_workers=10) as executor:
            results_list = executor.map(check_link, external_links)
            broken_links = [link for link in results_list if link]

        if broken_links:
            results["results"]["links"]["broken_external_links"] = {
                "value": False,
                "status": "Needs Improvement",
                "rating": 1,
                "reason": f"Broken external links found: {', '.join(broken_links)}"
            }
        else:
            results["results"]["links"]["broken_external_links"] = {
                "value": True,
                "status": "Good",
                "rating": 9,
                "reason": "No broken external links found"
            }


    @measure_execution_time
    def check_redirects_minimized(url, results):
        try:
            response = requests.get(url, allow_redirects=True, timeout=5)
            redirect_count = len(response.history)
            results["results"]["performance"]["redirects_minimized"] = {
                "value": redirect_count <= 2, 
                "status": "Good" if redirect_count <= 2 else "Needs Improvement", 
                "rating": 10 if redirect_count <= 2 else 5, 
                "reason": f"{redirect_count} redirects"
                }
        except:
            results["results"]["performance"]["redirects_minimized"] = {
                "value": "Error", "status": "Error", "rating": 1, "reason": "Failed to check redirects"}


    @measure_execution_time
    def check_keyword_density(soup, results, target_keyword):
            if target_keyword:
                text = soup.get_text().lower()
                words = re.findall(r'\b\w+\b', text)
                keyword_count = Counter(words)[target_keyword.lower()]
                total_words = len(words)
                density = (keyword_count / total_words) * 100 if total_words > 0 else 0
                results["results"]["content"]["keyword_density"] = {"value": round(density, 2), "status": "Good" if 1 <= density <= 3 else "Needs Improvement", "rating": 9 if 1 <= density <= 3 else 5, "reason": f"Keyword density: {density}%"}
            else:
                results["results"]["content"]["keyword_density"] = {"value": "No target keyword", "status": "Info", "rating": 0, "reason": "No target keyword provided"}



    
    @measure_execution_time
    def check_content_freshness(url, soup, results):
        response = requests.head(url)
        last_modified = response.headers.get("Last-Modified")
        freshness_date = None

        if last_modified:
            try:
                freshness_date = parser.parse(last_modified)
            except ValueError:
                pass

        # Check meta tags for published/modified dates
        for meta in soup.find_all("meta"):
            if meta.get("name") in ["article:published_time", "article:modified_time", "date"]:
                try:
                    freshness_date = parser.parse(meta.get("content"))
                    break
                except ValueError:
                    pass

        # Extract dates from visible content
        body_text = soup.get_text()
        content_dates = re.findall(r"\b\d{4}-\d{2}-\d{2}\b", body_text)
        if content_dates:
            try:
                freshness_date = parser.parse(content_dates[0])
            except ValueError:
                pass

        # Decide freshness status
        if freshness_date:
            days_old = (datetime.utcnow().replace(tzinfo=freshness_date.tzinfo) - freshness_date).days
            status = "Good" if days_old <= 30 else "Needs Improvement"
            rating = 9 if days_old <= 30 else 5
            reason = f"Last update {days_old} days ago"
        else:
            status = "Unknown"
            rating = 0
            reason = "Could not determine last update date"

        results["results"]["content"]["content_freshness"] = {
            "value": freshness_date.strftime("%Y-%m-%d") if freshness_date else "Unknown",
            "status": status,
            "rating": rating,
            "reason": reason
        }

        
    @measure_execution_time
    def check_https_redirect(url, results):
        if url.startswith("http://"):
            try:
                https_url = url.replace("http://", "https://", 1)
                redirect_response = requests.get(https_url, allow_redirects=False, timeout=5)
                results["results"]["security"]["https_redirect"] = {"value": redirect_response.status_code in [301, 302], "status": "Good" if redirect_response.status_code in [301, 302] else "Needs Improvement", "rating": 10 if redirect_response.status_code in [301, 302] else 5, "reason": "HTTP redirects to HTTPS" if redirect_response.status_code in [301, 302] else "HTTP does not redirect to HTTPS"}
            except:
                results["results"]["security"]["https_redirect"] = {"value": False, "status": "Error", "rating": 1, "reason": "Failed to check HTTPS redirect"}
        else:
            results["results"]["security"]["https_redirect"] = {"value": "HTTPS already", "status": "Info", "rating": 0, "reason": "URL is already HTTPS"}


    @measure_execution_time
    def check_internal_linking_depth(soup, results):
        internal_links = [a['href'] for a in soup.find_all('a', href=True) if a['href'].startswith('/')]
        link_count = len(internal_links)

        results["results"]["links"]["internal_linking_depth"] = {
            "value": link_count,
            "status": "Good" if link_count > 5 else "Needs Improvement",
            "rating": 9 if link_count > 5 else 5,
            "reason": f"Page contains {link_count} internal links."
        }



    @measure_execution_time
    def check_external_linking_quality(soup, results, url):
        external_links = []
        base_domain = urlparse(url).netloc  # Extract domain from the provided URL
        for a in soup.find_all('a', href=True):
            link = a["href"]
            parsed_link = urlparse(link)
            # Check if it's an external link (different domain)
            if parsed_link.netloc and parsed_link.netloc != base_domain:
                external_links.append(link)
        link_count = len(external_links)
        results["results"]["links"]["external_linking_quality"] = {
            "value": link_count,  # Corrected: Removed unnecessary quotes
            "status": "Good" if link_count > 0 else "Needs Improvement",  # Corrected spelling
            "rating": 9 if link_count > 0 else 5, 
            "reason": f"Page contains {link_count} external link(s)"
        }



# ==============================================================================================================
    @measure_execution_time
    def check_page_depth(url, results):
        try:
            parsed_url = urlparse(url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

            visited = {base_url}
            queue = deque([(base_url, 0)])  # (url, depth)

            while queue:
                current_url, depth = queue.popleft()

                if current_url == url:
                    results["results"]["url"]["page_depth"] = {
                        "value": depth,
                        "status": "Good" if depth <= 3 else "Needs Improvement",
                        "rating": 10 if depth <= 3 else 5,
                        "reason": f"Page depth: {depth}",
                    }
                    return

                try:
                    response = requests.get(current_url, timeout=5)
                    response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
                    soup = BeautifulSoup(response.content, "html.parser")
                    links = [urljoin(current_url, a.get("href")) for a in soup.find_all("a", href=True)]

                    for link in links:
                        if link.startswith(base_url) and link not in visited:
                            visited.add(link)
                            queue.append((link, depth + 1))

                except requests.exceptions.RequestException as e:
                    print(f"Error fetching {current_url}: {e}")
                    continue #skip to the next link.

            # If the URL was not found
            results["results"]["url"]["page_depth"] = {
                "value": "Not found",
                "status": "Error",
                "rating": 1,
                "reason": "URL not found during crawling",
            }

        except Exception as e:
            results["results"]["url"]["page_depth"] = {
                "value": "Error",
                "status": "Error",
                "rating": 1,
                "reason": f"Error calculating page depth: {e}",
            }
# ===========================================================================================================
    @measure_execution_time
    def check_content_readability(soup, results):
        try:
            text = str(soup)  # Convert soup to string
            tree = html.fromstring(text)
            doc = Document(text)  # Use Document instead of Readability
            readability_score = len(doc.summary())  # Just an example metric
            results["results"]["content"]["content_readability"] = {
                "value": readability_score,
                "status": "Good" if readability_score > 50 else "Needs Improvement",
                "rating": 9 if readability_score > 50 else 5,
                "reason": f"Readability Score: {readability_score}"
            }
        except Exception as e:
            print("Error:", e)



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
            "reasons":"Social meta tags present" if has_social_tags else "Missing social meta tags"
        }

    @measure_execution_time
    def check_favicon_exists(soup, url, results):
    # Check if favicon is declared in HTML
        favicon_tag = soup.find("link", rel=lambda r: r and "icon" in r.lower())
        favicon_url = urljoin(url, favicon_tag["href"]) if favicon_tag and "href" in favicon_tag.attrs else None

        if favicon_url:
            # Perform a quick HTTP HEAD request only if a favicon link is found
            try:
                response = requests.head(favicon_url, timeout=5)
                if response.status_code == 200:
                    results["results"]["meta_tags"]["favicon_exists"] = {
                        "value": favicon_url,
                        "status": "Good",
                        "rating": 10,
                        "reason": f"Favicon found and accessible"
                    }
                    return  # Stop checking further
            except requests.exceptions.RequestException:
                pass  # Ignore request errors

        # Fallback: Check /favicon.ico in root directory
        root_favicon_url = urljoin(url, "/favicon.ico")
        try:
            response = requests.head(root_favicon_url, timeout=5)
            if response.status_code == 200:
                results["results"]["meta_tags"]["favicon_exists"] = {
                    "value": True,
                    "status": "Good",
                    "rating": 10,
                    "reason": "Root favicon found and accessible"
                }
                return
        except requests.exceptions.RequestException:
            pass

        # If favicon is missing
        results["results"]["meta_tags"]["favicon_exists"] = {
            "value": False,
            "status": "Poor",
            "rating": 5,
            "reason": "Favicon not found"
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
            "reason": f"Text-to-HTML ratio: {ratio:.2f}"
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
            "reason": f"Number of iframes: {iframe_count}"
        }

    @measure_execution_time
    def check_flash_usage(soup, results):
        flash_count = sum(1 for tag in soup.find_all(["embed", "object"]) 
                        if tag.get("type") == "application/x-shockwave-flash")

        results["results"]["content"]["flash_usage"] = {
            "value": flash_count,
            "status": "Poor" if flash_count > 0 else "Good",
            "rating": 1 if flash_count > 0 else 10,
            "reason": f"{flash_count} Flash elements found"
        }


    @measure_execution_time
    async def check_broken_resource_link(soup, url, results):
        """Asynchronously checks for broken resource links (images, CSS, JS files)."""
        async def fetch_head(session, url):
            """Helper function to send an async HEAD request."""
            try:
                async with session.head(url, timeout=5) as response:
                    return url, response.status
            except aiohttp.ClientError:
                return url, None  # Return None if request fails

        resources = soup.find_all(["img", "link", "script"])
        broken_links = []
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            for resource in resources:
                resource_url = resource.get("src") if resource.name in ["img", "script"] else resource.get("href")
                if resource_url:
                    absolute_url = urljoin(url, resource_url)
                    tasks.append(fetch_head(session, absolute_url))
            
            responses = await asyncio.gather(*tasks)  # Execute all requests concurrently

            # Check responses for broken links
            broken_links = [res_url for res_url, status in responses if status is None or status >= 400]

        # Store results in the 'results' dictionary
        results["results"]["content"]["broken_resource_links"] = {
            "value": len(broken_links),
            "status": "Needs Improvement" if broken_links else "Good",
            "rating": 4 if broken_links else 10,
            "reason": f"Found {len(broken_links)} broken resource links" if broken_links else "No broken resource links found"
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
            "reason": f"Lists found: {list_count}"
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
            "reason": f"Tables found: {table_count}"
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
                    else "Viewport meta tag missing or not properly configured"
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
            "reason": "Duplicate title tag found" if is_duplicate else "Title tag is unique"
        }
        # Append the title to the list of all titles
        results["results"]["meta_tags"]["all_titles"].append(title_text)



    @measure_execution_time
    async def check_page_load_time(response, results):
        if not response or not hasattr(response, "elapsed"):
            results["results"]["performance"]["page_load_time"] = {
                "value": None,
                "status": "Error",
                "rating": 1,
                "reason": "Failed to measure load time, no response object"
            }
            return
        load_time = round(response.elapsed.total_seconds(), 2)
        results["results"]["performance"]["page_load_time"] = {
            "value": load_time,
            "status": "Good" if load_time <= 3 else "Needs Improvement",
            "rating": 10 if load_time <= 3 else 5,
            "reason": f"Page load time: {load_time} seconds"
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
            "reason": reason
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
                "suggestion": "Use headings (H1-H6) to structure your content properly."
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
                "suggestion": "Add an H1 tag to define the main topic of the page."
            }

        if skipped_levels:
            results["results"]["headings"]["heading_structure"]={
                "value": f"Skipped levels: {', '.join(skipped_levels)}",
                "status": "Needs Improvement",
                "rating": 3,
                "reason": f"Heading levels skipped: {', '.join(skipped_levels)}",
                "suggestion": "Use sequential heading levels (e.g., H1 → H2 → H3) for better structure."
            }
        else:
            results["results"]["headings"]["heading_structure"]={
                "value": "Correct heading structure",
                "status": "Good",
                "rating": 9,
                "reason": "Headings are in correct order.",
                "found_headings": found_headings  # Logs which headings exist
            }



    # Execute all checks
    seo_checks=[
        (check_meta_tags, (soup, results)),
        (check_headings, (soup, results)),
        (check_content, (soup, results)),
        (check_technical, (soup, results)),
        (check_performance, (soup, results, response if 'response' in locals() else None)),
        (check_security, (soup, results)),
        (check_mobile, (soup, results)),
        (check_url, (soup, results)),
        (check_schema, (soup, results)),
        (check_links, (soup, results)),
        # (check_validation, (soup, results)),
        (check_responsive_design, (soup, results)),
        (check_canonical_tag_valid, (soup, results, url)),
        (check_robots_meta_tag_exists, (soup, results)),
        (check_noindex_tag_check, (soup, results)),
        (check_nofollow_tag_check, (soup, results)),
        (check_image_file_size_optimized, (soup, results, url)),
        (check_image_dimensions_specified, (soup, results)),
        (check_broken_internal_links, (soup, results)),
        (check_broken_external_links, (soup, results, url)),
        (check_nofollow_on_external_links, (soup, results)),
        (check_gzip_compression_enabled, (response, results)),
        (check_browser_caching_enabled, (response, results)),
        (check_redirects_minimized, (url, results)),
        (check_xml_sitemap_exists, (url, results)),
        (check_keyword_in_title, (soup, results, target_keyword)),
        (check_keyword_in_h1, (soup, results, target_keyword)),
        (check_keyword_density, (soup, results, target_keyword)),
        (check_content_freshness, (url, soup, results)),
        (check_https_redirect, (url, results)),
        (check_internal_linking_depth, (soup, results)),
        (check_external_linking_quality, (soup, results, url)),
        (check_dublicate_title_tags, (soup, results)),
        (check_duplicate_content, (soup, results)),
        (check_page_depth, (url, results)),
        (check_content_readability, (soup, results)),
        (check_social_meta_tags, (soup, results)),
        (check_favicon_exists, (soup, url, results)),
        (check_text_to_html_ratio, (soup, results)),
        (check_iframe_usage, (soup, results)),
        (check_flash_usage, (soup, results)),
        (check_broken_resource_link, (soup, url, results)),
        (check_content_has_lists, (soup, results)),
        (check_content_has_tables, (soup, results)),
        (check_page_load_time, (response, results)),
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
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_check={executor.submit(func, *args):func for func, args in sync_checks}

        for future in as_completed(future_to_check):
            try:
                future.result()
            except Exception as e:
                check_name=future_to_check[future].__name__
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
    results["seo_rating"] = round(total / count, 2) if count else 0

    return dict(results)