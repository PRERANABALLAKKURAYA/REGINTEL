"""
Migration script to translate existing PMDA and NMPA updates in the database from Japanese to English
"""
import sys
from app.db.session import SessionLocal
from app.models.update import Update
from app.models.authority import Authority
from app.services.translation_service import translate_update

def migrate_translations():
    db = SessionLocal()
    
    try:
        # Get PMDA and NMPA authorities
        pmda = db.query(Authority).filter(Authority.name == "PMDA").first()
        nmpa = db.query(Authority).filter(Authority.name == "NMPA").first()
        
        authorities_to_translate = []
        if pmda:
            authorities_to_translate.append(pmda.id)
        if nmpa:
            authorities_to_translate.append(nmpa.id)
        
        if not authorities_to_translate:
            print("No PMDA or NMPA authorities found in database")
            return
        
        # Get all updates for these authorities
        updates = db.query(Update).filter(
            Update.authority_id.in_(authorities_to_translate)
        ).all()
        
        print(f"Found {len(updates)} updates to translate")
        
        translated_count = 0
        for update in updates:
            authority_name = pmda.name if update.authority_id == pmda.id else (nmpa.name if update.authority_id == nmpa.id else "Unknown")
            
            # Translate title and summary
            translated_title, translated_summary = translate_update(
                update.title,
                update.short_summary,
                authority=authority_name
            )
            
            # Check if translation changed anything
            title_changed = translated_title != update.title
            summary_changed = translated_summary and translated_summary != update.short_summary
            
            if title_changed or summary_changed:
                update.title = translated_title
                if translated_summary:
                    update.short_summary = translated_summary
                translated_count += 1
                print(f"[{authority_name}] Translated: {update.title[:80]}")
        
        # Commit changes
        db.commit()
        print(f"\nSuccessfully translated {translated_count} updates")
        
    except Exception as e:
        db.rollback()
        print(f"Error during migration: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("Starting translation migration...")
    migrate_translations()
    print("Migration complete!")
