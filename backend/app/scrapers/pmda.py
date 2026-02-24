from typing import List, Dict, Any
from datetime import datetime
from urllib.parse import urljoin
import re
from app.scrapers.base import BaseScraper


class PMDAScraper(BaseScraper):
    def __init__(self):
        super().__init__("PMDA", "https://www.pmda.go.jp")
        self.authority_country = "Japan"
        self.news_url = "https://www.pmda.go.jp/"

    def scrape(self) -> List[Dict[str, Any]]:
        updates: List[Dict[str, Any]] = []
        page = self.fetch_page(self.news_url)
        if not page:
            return updates

        section = page.select_one("section.section__news")
        if not section:
            return updates

        items = section.select("li")
        for item in items[:20]:
            link = item.find("a")
            if not link:
                continue

            href = link.get("href") or ""
            title_raw = link.get_text(strip=True)
            if not href or not title_raw:
                continue

            date_match = re.search(r"(\d{4})\u5e74(\d{1,2})\u6708(\d{1,2})\u65e5", title_raw)
            if date_match:
                year, month, day = map(int, date_match.groups())
                published = datetime(year, month, day)
            else:
                published = datetime.utcnow()

            title = re.sub(r"^\d{4}\u5e74\d{1,2}\u6708\d{1,2}\u65e5", "", title_raw)
            title = re.sub(r"\bNew\b", "", title).strip()

            source_link = urljoin(self.base_url.rstrip("/") + "/", href)
            updates.append(
                {
                    "title": title,
                    "category": "Notice",
                    "published_date": published,
                    "source_link": source_link,
                    "full_text": title,
                    "short_summary": title[:220],
                }
            )

        return updates
