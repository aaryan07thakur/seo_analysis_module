from bs4 import BeautifulSoup
import requests

# List of SEO rules
SEO_RULES = [
    {"name": "title_tag_exists", "description": "Check if <title> tag exists"},
    {"name": "h1_tag_unique", "description": "Check if <h1> tag is unique on the page"},
    {"name": "h2_tags_exist", "description": "Check if <h2> tags exist"},
    {"name": "alt_attributes_exist", "description": "Check if all images have alt attributes"},
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
]

# Function to evaluate SEO rules
def evaluate_seo_rules(soup, url):
    results = {}

    # Rule: Check if <title> tag exists
    title_tag = soup.title
    results["title_tag_exists"] = bool(title_tag)

    # Rule: Check if <h1> tag is unique
    h1_tags = soup.find_all("h1")
    results["h1_tag_unique"] = len(h1_tags) == 1

    # Rule: Check if <h2> tags exist
    h2_tags = soup.find_all("h2")
    results["h2_tags_exist"] = len(h2_tags) > 0

    # Rule: Check if all images have alt attributes
    images = soup.find_all("img")
    results["alt_attributes_exist"] = all(img.get("alt") is not None for img in images)

    # Rule: Check page load time
    try:
        response = requests.get(url, timeout=3)
        results["page_load_time"] = response.elapsed.total_seconds() < 3
    except Exception:
        results["page_load_time"] = False

    # Rule: Check if the page is mobile-friendly
    viewport_meta = soup.find("meta", attrs={"name": "viewport"})
    results["responsive_design"] = bool(viewport_meta)

    # Rule: Check if canonical tag exists
    canonical_tag = soup.find("link", attrs={"rel": "canonical"})
    results["canonical_tag_exists"] = bool(canonical_tag)

    # Rule: Check if canonical tag points to a valid URL
    if canonical_tag:
        canonical_url = canonical_tag.get("href", "")
        try:
            canonical_response = requests.get(canonical_url, timeout=5)
            results["canonical_tag_valid"] = canonical_response.status_code == 200
        except Exception:
            results["canonical_tag_valid"] = False
    else:
        results["canonical_tag_valid"] = False

    # Rule: Check if robots meta tag exists
    robots_meta = soup.find("meta", attrs={"name": "robots"})
    results["robots_meta_tag_exists"] = bool(robots_meta)

    # Rule: Check if the page is marked as noindex
    if robots_meta:
        results["noindex_tag_check"] = "noindex" in robots_meta.get("content", "").lower()
    else:
        results["noindex_tag_check"] = False

    # Rule: Check if the page is marked as nofollow
    if robots_meta:
        results["nofollow_tag_check"] = "nofollow" in robots_meta.get("content", "").lower()
    else:
        results["nofollow_tag_check"] = False

    # Calculate SEO rating out of 10
    passed_rules = sum(results.values())
    total_rules = len(results)
    seo_rating = round((passed_rules / total_rules) * 10, 2)

    results["seo_rating"] = seo_rating

    return results