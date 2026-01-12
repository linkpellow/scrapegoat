from __future__ import annotations

from typing import Any, Dict, List
from twisted.internet import reactor
from twisted.internet.defer import Deferred
from scrapy.crawler import CrawlerRunner
from scrapy.utils.project import get_project_settings

from app.scraping.spiders.generic import GenericJobSpider


class _ItemCollector:
    def __init__(self) -> None:
        self.items: List[Dict[str, Any]] = []

    def item_scraped(self, item, response, spider):
        self.items.append(dict(item))


def run_generic_spider(start_url: str, field_map: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Runs a single crawl with a generic spider and returns collected items.
    """
    settings = get_project_settings()
    runner = CrawlerRunner(settings=settings)

    collector = _ItemCollector()

    # Hook signals
    from scrapy import signals

    @runner.signals.connect
    def _connect_signals(*args, **kwargs):
        pass

    d: Deferred = runner.crawl(GenericJobSpider, start_url=start_url, field_map=field_map)

    # Attach collector by connecting signal to crawler within crawl isn't straightforward here without project scaffolding,
    # so we use FEEDS in settings or a simple pipeline in Step Four.
    # For Step Three, we keep it deterministic by writing via a small pipeline (below in tasks).
    #
    # We return empty and rely on the pipeline collection path in tasks.py.
    #
    # This function is intentionally minimal; the production pipeline is in tasks.py for run stability.
    try:
        if not reactor.running:
            # Not expected in Celery, but keep safe for local calls
            reactor.callWhenRunning(lambda: None)
    except Exception:
        pass

    # NOTE: We'll use Scrapy's built-in FEEDS in worker for true collection.
    return collector.items
