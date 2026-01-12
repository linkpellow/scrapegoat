import scrapy
from parsel import Selector
from urllib.parse import urljoin
from typing import Optional
from app.scraping.extraction import extract_from_selector


class GenericJobSpider(scrapy.Spider):
    name = "generic_job_spider"

    def __init__(self, start_url: str, field_map: dict, crawl_mode: str = "single", list_config: Optional[dict] = None, **kwargs):
        super().__init__(**kwargs)
        self.start_urls = [start_url]
        self._field_map = field_map
        self._crawl_mode = crawl_mode
        self._list_config = list_config or {}

        self._seen_detail_urls = set()
        self._pages_crawled = 0
        self._items_emitted = 0

    def parse(self, response):
        self._pages_crawled += 1

        if self._crawl_mode == "list":
            yield from self._parse_list(response)
        else:
            yield self._extract_detail(response)

    def _parse_list(self, response):
        max_pages = int(self._list_config.get("max_pages", 10))
        max_items = int(self._list_config.get("max_items", 500))

        item_links_spec = self._list_config.get("item_links", {})
        pagination_spec = self._list_config.get("pagination", {})

        # 1) Extract detail URLs
        sel = Selector(response.text)
        links = extract_from_selector(sel, item_links_spec)
        if links and not isinstance(links, list):
            links = [links]
        links = links or []

        for href in links:
            if self._items_emitted >= max_items:
                break
            abs_url = urljoin(response.url, href)
            if abs_url in self._seen_detail_urls:
                continue
            self._seen_detail_urls.add(abs_url)
            yield response.follow(abs_url, callback=self._parse_detail_page)

        # 2) Pagination
        if self._pages_crawled >= max_pages:
            return

        next_href = extract_from_selector(sel, pagination_spec)
        if isinstance(next_href, list):
            next_href = next_href[0] if next_href else None

        if next_href:
            next_url = urljoin(response.url, next_href)
            yield response.follow(next_url, callback=self.parse)

    def _parse_detail_page(self, response):
        if self._items_emitted >= int(self._list_config.get("max_items", 500)):
            return
        item = self._extract_detail(response)
        self._items_emitted += 1
        yield item

    def _extract_detail(self, response):
        sel = Selector(response.text)
        item = {"_meta": {"url": response.url, "status": response.status, "engine": "scrapy"}}
        for field_name, spec in self._field_map.items():
            item[field_name] = extract_from_selector(sel, spec)
        return item
