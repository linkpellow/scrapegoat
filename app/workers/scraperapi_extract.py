"""
ScraperAPI Extraction - Free alternative to ScrapingBee

ScraperAPI provides 5000 free credits per API key.
This module handles extraction using ScraperAPI with usage tracking.
"""
from typing import Dict, Any, List, Optional
import httpx
import logging
from urllib.parse import urljoin

from app.config import settings
from app.scraping.extraction import extract_from_html_css
from app.services.api_key_manager import ApiKeyManager

logger = logging.getLogger(__name__)


def _extract_with_scraperapi(
    url: str,
    field_map: Dict[str, Any],
    crawl_mode: str = "single",
    list_config: Dict[str, Any] = None
) -> List[Dict[str, Any]]:
    """
    Extract data using ScraperAPI (free alternative to ScrapingBee).
    
    Supports both single-page and list crawling modes.
    Tracks API key usage automatically.
    
    ScraperAPI provides 5000 free credits per API key.
    Each request consumes 1 credit.
    """
    scraperapi_url = "http://api.scraperapi.com"
    
    # Get available API key
    key_manager = ApiKeyManager()
    key_result = key_manager.get_available_key("scraperapi")
    
    if not key_result:
        logger.error("No available ScraperAPI keys with credits!")
        raise ValueError("No available ScraperAPI keys with credits")
    
    api_key, usage_record = key_result
    logger.info(f"ScraperAPI: Using key with {usage_record.remaining_credits}/{usage_record.total_credits} credits remaining")
    
    def _extract_fields(html: str) -> Dict[str, Any]:
        """Extract all fields from HTML using field_map"""
        item = {}
        for field_name, spec in field_map.items():
            value = extract_from_html_css(html, spec)
            if value is not None:
                item[field_name] = value
        return item
    
    def _make_request(target_url: str) -> Optional[str]:
        """Make a ScraperAPI request and track usage."""
        params = {
            'api_key': api_key,
            'url': target_url,
            'render': 'true',  # Enable JavaScript rendering
            'country_code': 'us'  # US-based proxies
        }
        
        try:
            response = httpx.get(scraperapi_url, params=params, timeout=60.0)
            
            # Check for errors
            if response.status_code >= 400:
                logger.error(f"ScraperAPI error {response.status_code}: {response.text[:500]}")
                
                # Check if it's an authentication/credit error
                if response.status_code == 401 or response.status_code == 403:
                    # Mark key as potentially exhausted
                    logger.warning(f"ScraperAPI authentication failed - key may be exhausted")
                    key_manager.record_usage("scraperapi", api_key, 0)  # Mark as used but don't consume credit
                    return None
                
                response.raise_for_status()
            
            # Record successful usage (1 credit per request)
            key_manager.record_usage("scraperapi", api_key, 1)
            
            html = response.text
            
            # Check if response is actually blocked
            if len(html) < 5000 and any(marker in html.lower() for marker in ["cloudflare", "challenge", "blocked"]):
                logger.warning("⚠️ Response appears to be blocked - returning empty")
                return None
            
            logger.info(f"✅ ScraperAPI success: received {len(html)} bytes")
            return html
            
        except Exception as e:
            logger.error(f"ScraperAPI request failed: {e}")
            # Don't record usage on failure
            raise
    
    if crawl_mode == "list":
        # List mode: extract list items and optionally paginate
        all_items = []
        visited_urls = set()
        current_url = url
        page_count = 0
        max_pages = 10  # Safety limit
        
        while current_url and page_count < max_pages:
            if current_url in visited_urls:
                break
            
            visited_urls.add(current_url)
            page_count += 1
            
            # Fetch page via ScraperAPI
            html = _make_request(current_url)
            if not html:
                break
            
            # For list mode, extract multiple items from the page
            if list_config and list_config.get("item_links"):
                # Extract list of item URLs
                item_links_spec = list_config["item_links"]
                item_urls = extract_from_html_css(html, item_links_spec)
                
                if not isinstance(item_urls, list):
                    item_urls = [item_urls] if item_urls else []
                
                # Fetch and extract each item (limit to avoid too many requests)
                for item_url in item_urls[:20]:  # Limit to 20 items per page
                    full_item_url = urljoin(current_url, item_url)
                    
                    # Fetch item detail page
                    item_html = _make_request(full_item_url)
                    if not item_html:
                        continue
                    
                    # Extract fields from item page
                    item = _extract_fields(item_html)
                    if item:
                        item['_url'] = full_item_url
                        all_items.append(item)
            else:
                # No item links - extract fields directly from list page
                item = _extract_fields(html)
                if item:
                    item['_url'] = current_url
                    all_items.append(item)
            
            # Find next page link if pagination configured
            if list_config and list_config.get("pagination"):
                pagination_spec = list_config["pagination"]
                next_href = extract_from_html_css(html, pagination_spec)
                
                if next_href:
                    current_url = urljoin(current_url, next_href)
                else:
                    current_url = None
            else:
                current_url = None
        
        return all_items
    
    else:
        # Single page mode
        html = _make_request(url)
        if not html:
            return []
        
        item = _extract_fields(html)
        return [item] if item else []
