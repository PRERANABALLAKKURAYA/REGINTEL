from app.models.notification import Notification
from app.models.user import User
from app.db.session import SessionLocal

class NotificationService:
    def __init__(self):
        pass

    def create_notification(self, user_id: int, update_id: int, message: str):
        db = SessionLocal()
        try:
            notif = Notification(user_id=user_id, update_id=update_id, is_read=False)
            db.add(notif)
            db.commit()
            
            # Logic to send email/Telegram would go here
            # self.send_email(user_id, message)
            print(f"Notification queued for User {user_id}: {message}")
            
        except Exception as e:
            print(f"Error creating notification: {e}")
            db.rollback()
        finally:
            db.close()

    def send_email(self, user_id: int, message: str):
        # Mock email sending
        print(f"Sending email to User {user_id}: {message}")

notification_service = NotificationService()
