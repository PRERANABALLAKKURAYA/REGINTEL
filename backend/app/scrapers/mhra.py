from typing import List, Dict, Any
from app.scrapers.base import BaseScraper


class MHRAScraper(BaseScraper):
    def __init__(self):
        super().__init__("MHRA", "https://www.gov.uk")
        self.authority_country = "UK"
        self.feed_url = (
            "https://www.gov.uk/government/organisations/"
            "medicines-and-healthcare-products-regulatory-agency.atom"
        )

    def scrape(self) -> List[Dict[str, Any]]:
        updates = self.parse_rss(self.feed_url, category="Notice")
        # Return empty if RSS fails - no homepage fallback
        return updates
