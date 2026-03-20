#!/usr/bin/env python
"""Script to add pdf_file_path column to update table"""

from app.db.session import SessionLocal
from sqlalchemy import text

def migrate():
    db = SessionLocal()
    try:
        # Add pdf_file_path column if it doesn't exist
        db.execute(text('ALTER TABLE "update" ADD COLUMN pdf_file_path VARCHAR NULL'))
        db.commit()
        print("✓ Migration applied: Added pdf_file_path column to update table")
    except Exception as e:
        db.rollback()
        if "duplicate column" in str(e).lower():
            print("✓ Column already exists, skipping")
        else:
            print(f"✗ Migration failed: {str(e)}")
            raise
    finally:
        db.close()

if __name__ == "__main__":
    migrate()
