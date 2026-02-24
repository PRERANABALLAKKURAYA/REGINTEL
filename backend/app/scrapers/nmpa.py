from typing import List, Dict, Any
from datetime import datetime
from urllib.parse import urljoin
import re
from app.scrapers.base import BaseScraper


class NMPAScraper(BaseScraper):
    def __init__(self):
        super().__init__("NMPA", "https://www.nmpa.gov.cn")
        self.authority_country = "China"
        self.announcements_url = "https://www.nmpa.gov.cn/xxgk/ggtg/"

    def scrape(self) -> List[Dict[str, Any]]:
        updates: List[Dict[str, Any]] = []
        page = self.fetch_page(self.announcements_url)
        if not page:
            return updates

        candidates: List[Dict[str, Any]] = []
        for link in page.find_all("a", href=True):
            href = link.get("href")
            if not href or "/xxgk/ggtg/" not in href or not href.endswith(".html"):
                continue

            title = link.get_text(strip=True)
            parent_text = link.parent.get_text(" ", strip=True)
            date_match = re.search(r"\((\d{4}-\d{2}-\d{2})\)", parent_text)
            if not date_match:
                continue

            date_str = date_match.group(1)
            try:
                published = datetime.strptime(date_str, "%Y-%m-%d")
            except Exception:
                published = datetime.utcnow()

            source_link = urljoin(self.base_url.rstrip("/") + "/", href)
            candidates.append(
                {
                    "title": title,
                    "category": "Notice",
                    "published_date": published,
                    "source_link": source_link,
                    "full_text": title,
                    "short_summary": title[:220],
                }
            )

        updates = candidates[:20]
        return updates
