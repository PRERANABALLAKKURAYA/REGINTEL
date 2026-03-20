from typing import List, Dict, Any
from datetime import datetime
import feedparser
from app.scrapers.base import BaseScraper


class FDAScraper(BaseScraper):
    def __init__(self):
        super().__init__("FDA", "https://www.fda.gov")
        self.authority_country = "USA"
        self.feed_url = "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/recalls/rss.xml"

    def scrape(self) -> List[Dict[str, Any]]:
        """FDA scraper using feedparser directly (requests to FDA are often blocked)."""
        feed = feedparser.parse(self.feed_url)
        updates: List[Dict[str, Any]] = []

        for entry in getattr(feed, "entries", [])[:20]:
            published = datetime.utcnow()
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                published = datetime(*entry.published_parsed[:6])
            elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                published = datetime(*entry.updated_parsed[:6])

            raw_link = getattr(entry, "link", "") or ""
            source_link = self._normalize_source_link(raw_link)
            if source_link and source_link.startswith("http://www.fda.gov"):
                source_link = source_link.replace("http://", "https://", 1)

            if not source_link:
                continue

            summary = getattr(entry, "summary", "") or ""
            updates.append(
                {
                    "title": getattr(entry, "title", "FDA Update"),
                    "category": "Recall",
                    "published_date": published,
                    "source_link": source_link,
                    "full_text": summary,
                    "short_summary": summary[:220] if summary else "",
                }
            )

        return updates
