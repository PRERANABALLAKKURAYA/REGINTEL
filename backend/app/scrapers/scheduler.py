import os
import threading
import time
from datetime import datetime
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
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


def _safe_log(message: str) -> None:
    """Log without crashing on non-cp1252 characters in some Windows consoles."""
    try:
        print(message)
    except UnicodeEncodeError:
        print(message.encode("ascii", errors="backslashreplace").decode("ascii"))


def run_scrapers() -> None:
    _safe_log(f"Running scrapers... {datetime.utcnow().isoformat()}")
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
            seen_source_links: set[str] = set()
            for item in updates:
                if not item.get("published_date"):
                    item["published_date"] = datetime.utcnow()

                source_link = (item.get("source_link") or "").strip()
                item["source_link"] = source_link

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

                if not source_link:
                    _safe_log(f"[SCRAPER] Skipping update with empty source_link for {scraper.authority_name}")
                    continue

                if source_link in seen_source_links:
                    _safe_log(f"[SCRAPER] Duplicate source_link in same batch skipped: {source_link}")
                    continue
                seen_source_links.add(source_link)

                # Check if guideline flag is provided (from guideline scrapers)
                is_guideline = item.get("is_guideline", False)

                try:
                    with db.begin_nested():
                        exists = db.query(Update).filter(Update.source_link == source_link).first()
                        if not exists:
                            item["authority_id"] = auth.id
                            db_obj = Update(**item)
                            db.add(db_obj)
                            inserted_count += 1
                            guideline_tag = "[GUIDELINE]" if is_guideline else "[UPDATE]"
                            _safe_log(
                                f"[SCRAPER] {guideline_tag} Inserted {scraper.authority_name} update: "
                                f"{item.get('title', '')[:80]} | {source_link}"
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
                                _safe_log(
                                    f"[SCRAPER] {guideline_tag} Updated {scraper.authority_name} update: "
                                    f"{item.get('title', '')[:80]} | {source_link}"
                                )
                except IntegrityError:
                    _safe_log(f"[SCRAPER] IntegrityError skipped for {scraper.authority_name} | {source_link}")
                    continue
                except Exception as item_error:
                    _safe_log(f"[SCRAPER] Item-level error for {scraper.authority_name} | {source_link}: {item_error}")
                    continue

            db.commit()
            _safe_log(
                f"Scraped {len(updates)} updates for {scraper.authority_name} "
                f"(inserted {inserted_count}, updated {updated_count})"
            )
        except Exception as e:
            _safe_log(f"Error scraping {scraper.authority_name}: {e}")
            db.rollback()

    distribution = (
        db.query(Authority.name, func.count(Update.id))
        .join(Update, Update.authority_id == Authority.id)
        .group_by(Authority.name)
        .order_by(Authority.name)
        .all()
    )
    _safe_log("[SCRAPER] Authority distribution:")
    for name, count in distribution:
        _safe_log(f"  {name}: {count}")

    db.close()


def _scheduler_loop(interval_minutes: int) -> None:
    try:
        run_scrapers()
    except Exception as startup_error:
        _safe_log(f"[SCHEDULER] Initial scrape loop error: {startup_error}")
    while True:
        time.sleep(interval_minutes * 60)
        try:
            run_scrapers()
        except Exception as loop_error:
            _safe_log(f"[SCHEDULER] Scheduled scrape loop error: {loop_error}")


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
