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
            # Create specific ICH guideline URL based on guideline category
            # ICH organizes guidelines by type: Q (Quality), E (Efficacy), S (Safety), M (Multidisciplinary)
            guideline_code = title.split(':')[0].replace('ICH ', '').strip()
            
            # Determine guideline category page
            first_letter = guideline_code[0].upper()
            if first_letter == 'Q':
                category_page = "quality-guidelines"
            elif first_letter == 'E':
                category_page = "efficacy-guidelines"
            elif first_letter == 'S':
                category_page = "safety-guidelines"
            elif first_letter == 'M':
                category_page = "multidisciplinary-guidelines"
            elif first_letter == 'Z':
                category_page = "ctd-guidelines"
            else:
                category_page = "ich-guidelines"
            
            # Create clean guideline identifier for anchor
            guideline_id = guideline_code.lower().replace('(', '').replace(')', '').replace(' ', '-')
            source_link = f"https://www.ich.org/page/{category_page}#{guideline_id}"
            
            updates.append({
                "title": title,
                "category": "Harmonisation Guideline",
                "published_date": now - timedelta(days=i*2),
                "source_link": source_link,
                "full_text": summary,
                "short_summary": summary[:220],
            })
        
        return updates
