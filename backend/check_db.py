from app.db.session import SessionLocal
from app.models.update import Update

db = SessionLocal()
updates = db.query(Update).all()
print(f'Total updates in DB: {len(updates)}')
for u in updates[:10]:
    authority = u.authority.name if u.authority else "No Authority"
    print(f'  {u.id}: {u.title[:60]}... ({authority})')
