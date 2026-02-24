from typing import List, Dict, Any
from app.scrapers.base import BaseScraper


class EMAScraper(BaseScraper):
    def __init__(self):
        super().__init__("EMA", "https://www.ema.europa.eu")
        self.authority_country = "EU"
        self.feed_url = "https://www.ema.europa.eu/en/news.xml"

    def scrape(self) -> List[Dict[str, Any]]:
        updates = self.parse_rss(self.feed_url, category="News")
        # Return empty if RSS fails - no homepage fallback
        return updates
