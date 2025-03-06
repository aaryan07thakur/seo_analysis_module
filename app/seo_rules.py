import requests
from bs4 import BeautifulSoup, NavigableString, Tag, Comment
from urllib.parse import urljoin, urlparse
import re
import textstat
from difflib import SequenceMatcher
import time
from collections import defaultdict

SEO_RULES = [
    {"name": "title_tag_exists", "description": "Check if <title> tag exists"},
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

    try:
        response = requests.get(url, timeout=10)
        headers = response.headers
        soup = BeautifulSoup(response.content, 'html.parser')
    except Exception as e:
        results["errors"]["base"] = str(e)
        return results

    # Meta Tags Evaluation
    def check_meta_tags(soup, results):
        title_tag = soup.title
        title_text = title_tag.string.strip() if title_tag and title_tag.string else ""
        # Define title_len BEFORE it's used:
        title_len = len(title_text)

        # Handle None explicitly if needed:
        title_value = title_tag.string if title_tag and title_tag.string else "Missing Title" if title_tag is None else None

        results["results"]["meta_tags"]["title_tag_exists"] = {
            "value": title_value,
            "status": "Good" if title_tag else "Poor",
            "rating": 10 if title_tag else 1,
            "reason": "Title tag present" if title_tag else "Missing title tag - critical for SEO"
        }

        results["results"]["meta_tags"]["title_tag_length"] = {
            "value": title_len,
            "status": "Good" if 50 <= title_len <= 60 else "Needs Improvement",
            "rating": 10 if 50 <= title_len <= 60 else 5,
            "reason": "Optimal length (50-60 chars)" if 50 <= title_len <= 60 else f"Title length: {title_len} chars (should be 50-60)"
        }
    meta_description = soup.find("meta", attrs={"name": "description"})
    desc_content = ""

    if isinstance(meta_description, Tag):
        content = meta_description.get("content")
        if isinstance(content, str):
            desc_content = content.strip()

    results["results"]["meta_tags"]["meta_description_exists"] = {
        "value": str(meta_description) if meta_description else False,
        "status": "Good" if meta_description else "Poor",
        "rating": 10 if meta_description else 1,
        "reason": "Meta description present" if meta_description else "Missing meta description"
    }
    results["results"]["meta_tags"]["meta_description_length"] = {
        "value": len(desc_content),
        "status": "Good" if 150 <= len(desc_content) <= 160 else "Needs Improvement",
        "rating": 9 if 150 <= len(desc_content) <= 160 else 5,
        "reason": "Optimal length (150-160 chars)" if 150 <= len(desc_content) <= 160 else f"Length: {len(desc_content)} chars (should be 150-160)"
    }

    # Headings Evaluation
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
            "value": len(h1_tags) == 1,
            "status": "Good" if len(h1_tags) == 1 else "Needs Improvement",
            "rating": 10 if len(h1_tags) == 1 else 5,
            "reason": "Single H1 tag" if len(h1_tags) == 1 else "Multiple H1 tags found"
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
    def check_performance(soup, results):
        # Page Load Time
        try:
            load_time = response.elapsed.total_seconds()
            results["results"]["performance"]["page_load_time"] = {
                "value": round(load_time, 2),
                "status": "Good" if load_time < 3 else "Needs Improvement",
                "rating": 10 if load_time < 3 else 5,
                "reason": f"Loaded in {load_time}s" if load_time < 3 else "Slow load time"
            }
        except:
            results["results"]["performance"]["page_load_time"] = {
                "value": None,
                "status": "Error",
                "rating": 1,
                "reason": "Failed to measure load time"
            }

    # Security
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
    def check_mobile(soup, results):
        viewport = soup.find("meta", attrs={"name": "viewport"})
        results["results"]["mobile"]["mobile_viewport"] = {
            "value": bool(viewport),
            "status": "Good" if viewport else "Needs Improvement",
            "rating": 10 if viewport else 5,
            "reason": "Mobile viewport configured" if viewport else "Missing viewport meta tag"
        }

    # Schema Markup
    def check_schema(soup, results):
        schema_tags = soup.find_all("script", type="application/ld+json")
        results["results"]["schema"]["schema_markup_exists"] = {
            "value": len(schema_tags) > 0,
            "status": "Good" if len(schema_tags) > 0 else "Needs Improvement",
            "rating": 8 if len(schema_tags) > 0 else 5,
            "reason": f"{len(schema_tags)} schema tags found" if schema_tags else "No schema markup"
        }

    # Link Analysis
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
    def check_validation(soup, results):
        html_errors = "Not implemented - requires W3C API"
        results["results"]["validation"]["html_validation"] = {
            "value": html_errors,
            "status": "Not Implemented",
            "rating": 0,
            "reason": "HTML validation requires external tools"
        }

    # Execute all checks
    check_meta_tags(soup, results)
    check_headings(soup,results)
    check_content(soup,results)
    check_technical(soup,results)
    check_performance(soup,results)
    check_security(soup,results)
    check_mobile(soup,results)
    check_url(soup,results)
    check_schema(soup,results)
    check_links(soup,results)
    check_validation(soup,results)

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