from sqlalchemy.orm import Session
from app.models.models import ShoppingReminder


class ShoppingReminderService:
    """Service for managing temporary shopping reminders."""

    def __init__(self, session: Session):
        self.session = session

    def add_reminders(self, items: list[str]) -> int:
        """Add multiple shopping reminder items. Returns count added."""
        added = 0
        for item in items:
            item = item.strip()
            if not item:
                continue
            # Check if already exists as active
            existing = self.session.query(ShoppingReminder).filter(
                ShoppingReminder.item_name == item,
                ShoppingReminder.active == True
            ).first()
            if not existing:
                reminder = ShoppingReminder(item_name=item, active=True)
                self.session.add(reminder)
                added += 1
        self.session.commit()
        return added

    def get_active_reminders(self) -> list[str]:
        """Get all active shopping reminders."""
        reminders = self.session.query(ShoppingReminder).filter(
            ShoppingReminder.active == True
        ).order_by(ShoppingReminder.created_at).all()
        return [r.item_name for r in reminders]

    def clear_reminders(self) -> int:
        """Mark all active reminders as inactive. Returns count cleared."""
        reminders = self.session.query(ShoppingReminder).filter(
            ShoppingReminder.active == True
        ).all()
        count = len(reminders)
        for reminder in reminders:
            reminder.active = False
        self.session.commit()
        return count

    def delete_reminder(self, item_name: str) -> bool:
        """Delete a specific reminder by name."""
        reminder = self.session.query(ShoppingReminder).filter(
            ShoppingReminder.item_name == item_name,
            ShoppingReminder.active == True
        ).first()
        if reminder:
            reminder.active = False
            self.session.commit()
            return True
        return False

    def count_active(self) -> int:
        """Count active reminders."""
        return self.session.query(ShoppingReminder).filter(
            ShoppingReminder.active == True
        ).count()
