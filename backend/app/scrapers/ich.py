from typing import List, Dict, Any
from datetime import datetime, timedelta
from app.scrapers.base import BaseScraper


class ICHScraper(BaseScraper):
    def __init__(self):
        super().__init__("ICH", "https://www.ich.org")
        self.authority_country = "International"

    def scrape(self) -> List[Dict[str, Any]]:
        """
        ICH (International Council for Harmonisation) guidelines scraper.
        Provides sample data with ICH guidelines and harmonisation documents.
        In production, this would connect to the ICH API or feed.
        """
        # Sample ICH guidelines and harmonisation topics
        ich_topics = [
            ("ICH M9(R2) Guideline for Multidose Non-Injectable Routes", "Updated guideline for preservative efficacy testing"),
            ("ICH Q14: Analytical Procedure Development Revision 1", "Guidance on developing and validating analytical procedures"),
            ("ICH S2(R2): Genotoxicity Test Battery Updates", "Current standards for assessing genotoxic potential"),
            ("ICH E6(R2): Good Clinical Practice Addendum", "Updated GCP standards for clinical trial conduct"),
            ("ICH Z: Common Technical Document (CTD) Structure", "Harmonised international format for regulatory submissions"),
            ("ICH Q13: Development of Biotechnological Products", "Strategies for characterizing biotechnology products"),
            ("ICH Q1F: Stability - Long Term Testing Update", "Current requirements for stability study conduct"),
            ("ICH M9: Quality of Biotechnological Products - Stability Testing", "Stability testing principles for biopharmaceuticals"),
            ("ICH Q4B: Annex: Format/Presentation of Foreign Substance Information", "Standardized format for foreign substance data"),
            ("ICH E1A: Ethnic Factors in the Acceptability of Foreign Clinical Data", "Guidance on acceptability of foreign clinical data"),
            ("ICH S9: Nonclinical Evaluation for Anticancer Pharmaceuticals", "Nonclinical safety assessment for anticancer drugs"),
            ("ICH Q7: Good Manufacturing Practice for Active Pharmaceutical Ingredients", "Current GMP standards for API manufacturing"),
            ("ICH Q8(R2): Pharmaceutical Development Guidelines Revision", "Enhanced guidance on drug development and quality"),
            ("ICH E3: Structure and Content of Clinical Study Reports", "Format requirements for clinical study reports"),
            ("ICH E4: Dose-Response Information Assessment", "Guidelines for dose-response relationship evaluation"),
        ]
        
        updates: List[Dict[str, Any]] = []
        now = datetime.utcnow()
        
        for i, (title, summary) in enumerate(ich_topics):
            # Use ICH guidelines main page as source (real, working URL)
            source_link = "https://www.ich.org/page/guidelines"
            
            updates.append({
                "title": title,
                "category": "Harmonisation Guideline",
                "published_date": now - timedelta(days=i*2),
                "source_link": source_link,
                "full_text": summary,
                "short_summary": summary[:220],
            })
        
        return updates
