#!/usr/bin/env python3
"""
Isolated Scrapy Runner - Runs Scrapy in a subprocess to avoid ReactorNotRestartable.

This script is executed as a subprocess to run Scrapy with a fresh reactor each time.
"""
import json
import os
import sys
import tempfile
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from app.scraping.spiders.generic import GenericJobSpider
from app.config import settings

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Missing arguments"}))
        sys.exit(1)
    
    # Parse arguments
    args = json.loads(sys.argv[1])
    start_url = args["start_url"]
    field_map = args["field_map"]
    crawl_mode = args.get("crawl_mode", "single")
    list_config = args.get("list_config", {})
    timeout = args.get("timeout", 20)
    
    # Create temp directory for output
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = os.path.join(tmpdir, "items.json")
        
        # Configure Scrapy settings
        s = get_project_settings()
        custom_settings = {
            "LOG_ENABLED": False,
            "ROBOTSTXT_OBEY": False,
            "DOWNLOAD_TIMEOUT": timeout,
            "USER_AGENT": "scraper-platform/1.0",
            "FEEDS": {out_path: {"format": "json", "encoding": "utf8", "indent": 2}},
        }
        
        try:
            # Run Scrapy in this isolated process
            process = CrawlerProcess(settings={**dict(s), **custom_settings})
            process.crawl(
                GenericJobSpider,
                start_url=start_url,
                field_map=field_map,
                crawl_mode=crawl_mode,
                list_config=list_config,
            )
            process.start()  # This starts and stops the reactor cleanly
            
            # Read results
            if os.path.exists(out_path):
                with open(out_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    result = data if isinstance(data, list) else []
            else:
                result = []
            
            # Output JSON result
            print(json.dumps({"success": True, "items": result}))
            
        except Exception as e:
            # Output error as JSON
            print(json.dumps({"success": False, "error": str(e)}))
            sys.exit(1)
