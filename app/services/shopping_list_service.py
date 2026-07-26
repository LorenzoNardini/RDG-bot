from sqlalchemy.orm import Session
from app.models.models import ShoppingListItem


class ShoppingListService:
    """Manage the active shopping list (external ingredients + reminders combined)."""

    def __init__(self, session: Session):
        self.session = session

    def add_external_ingredients(self, recipe_id: int, ingredients: list[str]):
        """Add external ingredients from a recipe to the shopping list."""
        for ingredient in ingredients:
            item = ShoppingListItem(
                item_name=ingredient,
                source_type="external_ingredient",
                source_id=recipe_id
            )
            self.session.add(item)
        self.session.commit()

    def add_reminder(self, item_name: str):
        """Add a manual reminder to the shopping list."""
        item = ShoppingListItem(
            item_name=item_name,
            source_type="reminder",
            source_id=None
        )
        self.session.add(item)
        self.session.commit()

    def get_all_items(self) -> list[str]:
        """Get all items currently on the shopping list."""
        items = self.session.query(ShoppingListItem).all()
        return sorted(set([item.item_name for item in items]))

    def clear_all(self):
        """Clear the entire shopping list (when /bought is called)."""
        self.session.query(ShoppingListItem).delete()
        self.session.commit()

    def count_items(self) -> int:
        """Count items on the shopping list."""
        return self.session.query(ShoppingListItem).count()
