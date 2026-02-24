import os
import threading
import time
from datetime import datetime
from sqlalchemy import func
from app.db.session import SessionLocal
from app.models.update import Update
from app.models.authority import Authority
from app.scrapers.fda import FDAScraper
from app.scrapers.cdsco import CDSCOScraper
from app.scrapers.ema import EMAScraper
from app.scrapers.ich import ICHScraper
from app.scrapers.mhra import MHRAScraper
from app.scrapers.pmda import PMDAScraper
from app.scrapers.nmpa import NMPAScraper
from app.scrapers.guidelines import (
    EMAGuidelineScraper,
    FDAGuidelineScraper,
    MHRAGuidelineScraper,
    PMDAGuidelineScraper,
    CDSCOGuidelineScraper,
    NMPAGuidelineScraper,
    ICHGuidelineScraper,
)
from app.services.translation_service import translate_update

_scheduler_started = False


def run_scrapers() -> None:
    print("Running scrapers...", datetime.utcnow().isoformat())
    db = SessionLocal()
    
    # News/Updates scrapers
    news_scrapers = [
        FDAScraper(),
        CDSCOScraper(),
        EMAScraper(),
        ICHScraper(),
        MHRAScraper(),
        PMDAScraper(),
        NMPAScraper(),
    ]
    
    # Guideline scrapers
    guideline_scrapers = [
        FDAGuidelineScraper(),
        EMAGuidelineScraper(),
        MHRAGuidelineScraper(),
        PMDAGuidelineScraper(),
        CDSCOGuidelineScraper(),
        NMPAGuidelineScraper(),
        ICHGuidelineScraper(),
    ]
    
    all_scrapers = news_scrapers + guideline_scrapers

    for scraper in all_scrapers:
        try:
            updates = scraper.scrape()
            auth = db.query(Authority).filter(Authority.name == scraper.authority_name).first()
            if not auth:
                auth = Authority(
                    name=scraper.authority_name,
                    country=scraper.authority_country,
                    website_url=scraper.base_url,
                )
                db.add(auth)
                db.commit()
                db.refresh(auth)

            inserted_count = 0
            updated_count = 0
            for item in updates:
                if not item.get("published_date"):
                    item["published_date"] = datetime.utcnow()

                # Translate PMDA and NMPA updates to English
                if scraper.authority_name in ["PMDA", "NMPA"]:
                    translated_title, translated_summary = translate_update(
                        item.get("title", ""),
                        item.get("short_summary"),
                        authority=scraper.authority_name
                    )
                    item["title"] = translated_title
                    if translated_summary:
                        item["short_summary"] = translated_summary

                if not item.get("source_link"):
                    print(f"[SCRAPER] Skipping update with empty source_link for {scraper.authority_name}")
                    continue

                # Check if guideline flag is provided (from guideline scrapers)
                is_guideline = item.get("is_guideline", False)

                exists = db.query(Update).filter(Update.source_link == item["source_link"]).first()
                if not exists:
                    item["authority_id"] = auth.id
                    db_obj = Update(**item)
                    db.add(db_obj)
                    inserted_count += 1
                    guideline_tag = "[GUIDELINE]" if is_guideline else "[UPDATE]"
                    print(
                        f"[SCRAPER] {guideline_tag} Inserted {scraper.authority_name} update: "
                        f"{item.get('title', '')[:80]} | {item.get('source_link')}"
                    )
                else:
                    updated = False
                    if item.get("published_date") and exists.published_date != item["published_date"]:
                        exists.published_date = item["published_date"]
                        updated = True
                    if item.get("title") and exists.title != item["title"]:
                        exists.title = item["title"]
                        updated = True
                    if item.get("category") and exists.category != item["category"]:
                        exists.category = item["category"]
                        updated = True
                    if item.get("full_text") and exists.full_text != item["full_text"]:
                        exists.full_text = item["full_text"]
                        updated = True
                    if item.get("short_summary") and exists.short_summary != item["short_summary"]:
                        exists.short_summary = item["short_summary"]
                        updated = True
                    if is_guideline and not exists.is_guideline:
                        exists.is_guideline = True
                        updated = True

                    if updated:
                        updated_count += 1
                        guideline_tag = "[GUIDELINE]" if is_guideline else "[UPDATE]"
                        print(
                            f"[SCRAPER] {guideline_tag} Updated {scraper.authority_name} update: "
                            f"{item.get('title', '')[:80]} | {item.get('source_link')}"
                        )

            db.commit()
            print(
                f"Scraped {len(updates)} updates for {scraper.authority_name} "
                f"(inserted {inserted_count}, updated {updated_count})"
            )
        except Exception as e:
            print(f"Error scraping {scraper.authority_name}: {e}")
            db.rollback()

    distribution = (
        db.query(Authority.name, func.count(Update.id))
        .join(Update, Update.authority_id == Authority.id)
        .group_by(Authority.name)
        .order_by(Authority.name)
        .all()
    )
    print("[SCRAPER] Authority distribution:")
    for name, count in distribution:
        print(f"  {name}: {count}")

    db.close()


def _scheduler_loop(interval_minutes: int) -> None:
    run_scrapers()
    while True:
        time.sleep(interval_minutes * 60)
        run_scrapers()


def start_scheduler() -> None:
    global _scheduler_started
    if _scheduler_started:
        return
    _scheduler_started = True

    interval_minutes = int(os.getenv("SCRAPE_INTERVAL_MINUTES", "360"))
    thread = threading.Thread(target=_scheduler_loop, args=(interval_minutes,), daemon=True)
    thread.start()


if __name__ == "__main__":
    start_scheduler()
    while True:
        time.sleep(60)
