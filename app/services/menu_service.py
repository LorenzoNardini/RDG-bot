import random
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.models import WeeklyMenu, WeeklyMenuItem, Recipe
from app.services.recipe_service import RecipeService

CATEGORIES = ["carne rossa", "carne bianca", "pesce", "uova", "legumi", "altro"]


class MenuService:
    def __init__(self, session: Session):
        self.session = session
        self.recipe_service = RecipeService(session)

    def generate_week(self) -> WeeklyMenu | None:
        """
        Generate a new weekly menu.
        - Pick 1 recipe from each of 6 categories
        - Fill slot 7 with a random recipe from any category
        - No duplicates within the week
        - Returns a pending (not yet accepted) WeeklyMenu
        """
        # Get recipes for each category
        category_recipes = {}
        for category in CATEGORIES:
            recipes = self.recipe_service.get_by_category(category)
            if not recipes:
                return None  # Cannot generate if any category is empty
            category_recipes[category] = recipes

        # Create menu
        menu = WeeklyMenu()
        self.session.add(menu)
        self.session.flush()  # Get the menu ID

        selected_recipes = set()
        items = []

        # Pick one recipe per category for positions 1-6
        for position, category in enumerate(CATEGORIES, start=1):
            recipes = category_recipes[category]
            available = [r for r in recipes if r.id not in selected_recipes]
            if not available:
                available = recipes
            recipe = random.choice(available)
            selected_recipes.add(recipe.id)
            items.append(WeeklyMenuItem(menu_id=menu.id, recipe_id=recipe.id, position=position))

        # Pick any recipe for position 7
        all_recipes = self.recipe_service.get_all()
        available = [r for r in all_recipes if r.id not in selected_recipes]
        if available:
            recipe = random.choice(available)
            items.append(WeeklyMenuItem(menu_id=menu.id, recipe_id=recipe.id, position=7))

        for item in items:
            self.session.add(item)

        self.session.commit()
        return menu

    def get_pending_menu(self, menu_id: int) -> WeeklyMenu | None:
        """Get a pending menu by ID."""
        menu = self.session.query(WeeklyMenu).filter(WeeklyMenu.id == menu_id).first()
        if menu and menu.is_pending():
            return menu
        return None

    def get_menu(self, menu_id: int) -> WeeklyMenu | None:
        """Get a menu by ID (pending or accepted)."""
        return self.session.query(WeeklyMenu).filter(WeeklyMenu.id == menu_id).first()

    def get_menu_items(self, menu_id: int) -> list[WeeklyMenuItem]:
        """Get all items in a menu, sorted by position."""
        return self.session.query(WeeklyMenuItem).filter(
            WeeklyMenuItem.menu_id == menu_id
        ).order_by(WeeklyMenuItem.position).all()

    def reroll_category(self, menu_id: int, category: str) -> bool:
        """
        Reroll all items of a given category in the menu.
        Picks a new random recipe from that category, avoiding current selections.
        """
        # Get current menu
        menu = self.get_menu(menu_id)
        if not menu:
            return False

        # Get current selected recipes
        current_items = self.get_menu_items(menu_id)
        selected_recipe_ids = {item.recipe_id for item in current_items}

        # Find items of this category
        category_items = [item for item in current_items if item.recipe.category == category]
        if not category_items:
            return False

        # Get available recipes in this category
        recipes = self.recipe_service.get_by_category(category)
        available = [r for r in recipes if r.id not in selected_recipe_ids]
        if not available:
            available = recipes

        # Replace each item of this category with a new recipe
        for item in category_items:
            new_recipe = random.choice(available)
            # Remove from selection to avoid duplicates
            selected_recipe_ids.discard(item.recipe_id)
            selected_recipe_ids.add(new_recipe.id)
            item.recipe_id = new_recipe.id

        self.session.commit()
        return True

    def reroll_position(self, menu_id: int, position: int) -> bool:
        """
        Reroll the meal at a given position.
        - Positions 1-6: maintain category constraint (fixed per category)
        - Position 7: can pick any category (wild card slot)
        """
        # Get current menu
        menu = self.get_menu(menu_id)
        if not menu:
            return False

        # Get the item at this position
        item = self.session.query(WeeklyMenuItem).filter(
            WeeklyMenuItem.menu_id == menu_id,
            WeeklyMenuItem.position == position
        ).first()
        if not item:
            return False

        # Get current selected recipes (excluding this item)
        current_items = self.get_menu_items(menu_id)
        selected_recipe_ids = {i.recipe_id for i in current_items if i.position != position}

        if position <= 6:
            # Positions 1-6: maintain the original category
            original_category = item.recipe.category
            category_recipes = self.recipe_service.get_by_category(original_category)
            available = [r for r in category_recipes if r.id not in selected_recipe_ids]
            if not available:
                available = category_recipes
        else:
            # Position 7: pick from any category
            all_recipes = self.recipe_service.get_all()
            available = [r for r in all_recipes if r.id not in selected_recipe_ids]
            if not available:
                available = all_recipes

        # Replace with new recipe
        new_recipe = random.choice(available)
        item.recipe_id = new_recipe.id

        self.session.commit()
        return True

    def accept_menu(self, menu_id: int) -> bool:
        """
        Accept a pending menu.
        Sets accepted_at timestamp and marks the menu as accepted.
        """
        menu = self.get_menu(menu_id)
        if not menu:
            return False

        menu.accepted_at = datetime.utcnow()
        self.session.commit()
        return True

    def get_recent_accepted_menus(self, limit: int = 5) -> list[WeeklyMenu]:
        """Get recent accepted menus."""
        return self.session.query(WeeklyMenu).filter(
            WeeklyMenu.accepted_at.isnot(None)
        ).order_by(WeeklyMenu.accepted_at.desc()).limit(limit).all()

    def delete_menu(self, menu_id: int) -> bool:
        """Delete a menu and its items."""
        menu = self.get_menu(menu_id)
        if menu:
            self.session.delete(menu)
            self.session.commit()
            return True
        return False
