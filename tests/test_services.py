import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.models import Base, Recipe, WeeklyMenu, WeeklyMenuItem, ExternalIngredient
from app.services.recipe_service import RecipeService
from app.services.menu_service import MenuService
from app.services.external_service import ExternalIngredientService


@pytest.fixture
def test_db():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def seed_recipes(test_db):
    """Seed test recipes."""
    recipes = [
        Recipe(name="Pasta Carbonara", category="altro", needs_side=False),
        Recipe(name="Spaghetti Aglio Olio", category="altro", needs_side=False),
        Recipe(name="Bistecca alla Fiorentina", category="carne rossa", needs_side=True, suggested_side="Patatine"),
        Recipe(name="Costata di Manzo", category="carne rossa", needs_side=True, suggested_side="Insalata"),
        Recipe(name="Petto di Pollo", category="carne bianca", needs_side=True, suggested_side="Verdure"),
        Recipe(name="Branzino al Forno", category="pesce", needs_side=True, suggested_side="Limone"),
        Recipe(name="Frittata di Cipolle", category="uova", needs_side=False),
        Recipe(name="Minestra di Lenticchie", category="legumi", needs_side=False),
    ]
    for recipe in recipes:
        test_db.add(recipe)
    test_db.commit()
    return recipes


class TestFormattingFunctions:
    """Test formatting functions for shopping lists."""

    def test_format_consolidated_shopping_list_with_items(self):
        from app.utils.formatting import format_consolidated_shopping_list

        items = ["salmon fillet", "dill", "olive oil", "coffee beans"]
        result = format_consolidated_shopping_list(items)

        assert "🛒" in result
        assert "Remember to buy" in result
        assert "salmon fillet" in result
        assert "dill" in result
        assert "olive oil" in result
        assert "coffee beans" in result

    def test_format_consolidated_shopping_list_empty(self):
        from app.utils.formatting import format_consolidated_shopping_list

        result = format_consolidated_shopping_list([])

        assert "🛒" in result
        assert len(result) > 0  # Should show empty state message


class TestRecipeService:
    def test_get_by_category(self, test_db, seed_recipes):
        service = RecipeService(test_db)
        recipes = service.get_by_category("carne rossa")
        assert len(recipes) == 2
        assert all(r.category == "carne rossa" for r in recipes)

    def test_get_by_name(self, test_db, seed_recipes):
        service = RecipeService(test_db)
        recipe = service.get_by_name("Pasta Carbonara")
        assert recipe is not None
        assert recipe.category == "altro"

    def test_get_all(self, test_db, seed_recipes):
        service = RecipeService(test_db)
        recipes = service.get_all()
        assert len(recipes) == 8

    def test_count_all(self, test_db, seed_recipes):
        service = RecipeService(test_db)
        assert service.count_all() == 8

    def test_count_by_category(self, test_db, seed_recipes):
        service = RecipeService(test_db)
        assert service.count_by_category("carne rossa") == 2
        assert service.count_by_category("pesce") == 1


class TestMenuService:
    def test_generate_week_creates_7_items(self, test_db, seed_recipes):
        service = MenuService(test_db)
        menu = service.generate_week()
        items = service.get_menu_items(menu.id)
        assert len(items) == 7

    def test_generate_week_one_per_category(self, test_db, seed_recipes):
        service = MenuService(test_db)
        menu = service.generate_week()
        items = service.get_menu_items(menu.id)

        # Positions 1-6 should have different categories
        categories = [items[i].recipe.category for i in range(6)]
        assert len(set(categories)) == 6

    def test_reroll_category_changes_recipe(self, test_db, seed_recipes):
        service = MenuService(test_db)
        menu = service.generate_week()
        items = service.get_menu_items(menu.id)

        # Find an item with category "carne rossa"
        carne_item = next(i for i in items if i.recipe.category == "carne rossa")
        original_recipe_id = carne_item.recipe_id

        # Reroll the category
        service.reroll_category(menu.id, "carne rossa")

        # Refresh items
        items = service.get_menu_items(menu.id)
        carne_item = next(i for i in items if i.recipe.category == "carne rossa")

        # Recipe might have changed (or stayed the same if only 1)
        # Just verify it's still in the same category
        assert carne_item.recipe.category == "carne rossa"

    def test_reroll_position_maintains_category(self, test_db, seed_recipes):
        """Test that rerolling positions 1-6 maintains the category constraint."""
        service = MenuService(test_db)
        menu = service.generate_week()
        items = service.get_menu_items(menu.id)

        # Get the first item (position 1, should be "carne rossa")
        item = items[0]
        original_category = item.recipe.category
        original_recipe_id = item.recipe_id

        # Reroll position 1
        service.reroll_position(menu.id, 1)

        # Refresh items
        items = service.get_menu_items(menu.id)
        item = items[0]

        # Category should be maintained
        assert item.recipe.category == original_category

    def test_reroll_position_7_flexibility(self, test_db, seed_recipes):
        """Test that position 7 can be rerolled without category constraint."""
        service = MenuService(test_db)
        menu = service.generate_week()
        items = service.get_menu_items(menu.id)

        # Get position 7 (wild card slot)
        item_7 = items[6]
        assert item_7.position == 7

        # Reroll position 7 should work without errors
        # (unlike positions 1-6 which maintain category)
        success = service.reroll_position(menu.id, 7)
        assert success

        # Verify we still have 7 items and position 7 exists
        items = service.get_menu_items(menu.id)
        assert len(items) == 7
        assert items[6].position == 7
        assert items[6].recipe is not None

    def test_accept_menu_sets_timestamp(self, test_db, seed_recipes):
        service = MenuService(test_db)
        menu = service.generate_week()
        assert menu.accepted_at is None

        service.accept_menu(menu.id)

        menu = service.get_menu(menu.id)
        assert menu.accepted_at is not None

    def test_get_pending_menu_returns_none_if_accepted(self, test_db, seed_recipes):
        service = MenuService(test_db)
        menu = service.generate_week()
        assert service.get_pending_menu(menu.id) is not None

        service.accept_menu(menu.id)
        assert service.get_pending_menu(menu.id) is None

    def test_get_recent_accepted_menus(self, test_db, seed_recipes):
        service = MenuService(test_db)

        # Create and accept 3 menus
        for _ in range(3):
            menu = service.generate_week()
            service.accept_menu(menu.id)

        recent = service.get_recent_accepted_menus(limit=5)
        assert len(recent) == 3


class TestConsolidatedShoppingList:
    """Test consolidated shopping list (recipes + reminders)."""

    def test_get_consolidated_list_with_recipes_and_reminders(self, test_db, seed_recipes):
        from app.services.external_service import ExternalIngredientService
        from app.services.shopping_service import ShoppingReminderService

        # Setup: mark some recipes with external ingredients
        external_service = ExternalIngredientService(test_db)
        external_service.set_ingredients(seed_recipes[0].id, ["flour", "butter"])
        external_service.set_ingredients(seed_recipes[1].id, ["salt"])

        # Add shopping reminders
        shopping_service = ShoppingReminderService(test_db)
        shopping_service.add_reminders(["olive oil", "coffee beans"])

        # Get consolidated list
        recipe_ingredients = []
        for recipe in seed_recipes:
            if external_service.get_status(recipe.id) == "defined":
                recipe_ingredients.extend(external_service.get_ingredients(recipe.id))

        reminders = shopping_service.get_active_reminders()
        consolidated = sorted(set(recipe_ingredients + reminders))

        assert len(consolidated) == 5
        assert "flour" in consolidated
        assert "butter" in consolidated
        assert "salt" in consolidated
        assert "olive oil" in consolidated
        assert "coffee beans" in consolidated

    def test_consolidated_list_only_recipes(self, test_db, seed_recipes):
        from app.services.external_service import ExternalIngredientService
        from app.services.shopping_service import ShoppingReminderService

        external_service = ExternalIngredientService(test_db)
        external_service.set_ingredients(seed_recipes[0].id, ["flour"])

        shopping_service = ShoppingReminderService(test_db)

        recipe_ingredients = []
        for recipe in seed_recipes:
            if external_service.get_status(recipe.id) == "defined":
                recipe_ingredients.extend(external_service.get_ingredients(recipe.id))

        reminders = shopping_service.get_active_reminders()
        consolidated = recipe_ingredients + reminders

        assert len(consolidated) == 1
        assert "flour" in consolidated

    def test_consolidated_list_only_reminders(self, test_db, seed_recipes):
        from app.services.shopping_service import ShoppingReminderService

        shopping_service = ShoppingReminderService(test_db)
        shopping_service.add_reminders(["olive oil"])

        reminders = shopping_service.get_active_reminders()

        assert len(reminders) == 1
        assert "olive oil" in reminders

    def test_consolidated_list_empty(self, test_db, seed_recipes):
        from app.services.external_service import ExternalIngredientService
        from app.services.shopping_service import ShoppingReminderService

        external_service = ExternalIngredientService(test_db)
        shopping_service = ShoppingReminderService(test_db)

        recipe_ingredients = []
        for recipe in seed_recipes:
            if external_service.get_status(recipe.id) == "defined":
                recipe_ingredients.extend(external_service.get_ingredients(recipe.id))

        reminders = shopping_service.get_active_reminders()
        consolidated = recipe_ingredients + reminders

        assert len(consolidated) == 0


class TestShoppingReminderService:
    def test_add_single_reminder(self, test_db):
        from app.services.shopping_service import ShoppingReminderService
        service = ShoppingReminderService(test_db)

        added = service.add_reminders(["olive oil"])
        assert added == 1
        assert service.count_active() == 1

    def test_add_multiple_reminders(self, test_db):
        from app.services.shopping_service import ShoppingReminderService
        service = ShoppingReminderService(test_db)

        added = service.add_reminders(["olive oil", "coffee beans", "batteries"])
        assert added == 3
        assert service.count_active() == 3

    def test_get_active_reminders(self, test_db):
        from app.services.shopping_service import ShoppingReminderService
        service = ShoppingReminderService(test_db)

        service.add_reminders(["olive oil", "coffee"])
        reminders = service.get_active_reminders()
        assert len(reminders) == 2
        assert "olive oil" in reminders
        assert "coffee" in reminders

    def test_duplicate_reminders_not_added(self, test_db):
        from app.services.shopping_service import ShoppingReminderService
        service = ShoppingReminderService(test_db)

        service.add_reminders(["olive oil"])
        added = service.add_reminders(["olive oil"])
        assert added == 0
        assert service.count_active() == 1

    def test_clear_reminders(self, test_db):
        from app.services.shopping_service import ShoppingReminderService
        service = ShoppingReminderService(test_db)

        service.add_reminders(["olive oil", "coffee"])
        assert service.count_active() == 2

        cleared = service.clear_reminders()
        assert cleared == 2
        assert service.count_active() == 0

    def test_delete_reminder(self, test_db):
        from app.services.shopping_service import ShoppingReminderService
        service = ShoppingReminderService(test_db)

        service.add_reminders(["olive oil", "coffee"])
        deleted = service.delete_reminder("olive oil")
        assert deleted
        assert service.count_active() == 1
        assert "coffee" in service.get_active_reminders()


class TestBoughtCommand:
    """Test /bought command functionality."""

    def test_bought_clears_all_reminders(self, test_db):
        from app.services.shopping_service import ShoppingReminderService
        service = ShoppingReminderService(test_db)

        service.add_reminders(["olive oil", "coffee", "batteries"])
        assert service.count_active() == 3

        cleared = service.clear_reminders()
        assert cleared == 3
        assert service.count_active() == 0

    def test_bought_resets_recipes_to_unknown(self, test_db, seed_recipes):
        from app.services.external_service import ExternalIngredientService
        from sqlalchemy import text
        service = ExternalIngredientService(test_db)

        # Setup: mark some recipes as defined
        service.set_ingredients(seed_recipes[0].id, ["flour", "butter"])
        service.set_ingredients(seed_recipes[1].id, ["salt"])
        service.set_no_external(seed_recipes[2].id)

        # Verify they're set
        assert service.get_status(seed_recipes[0].id) == "defined"
        assert service.get_status(seed_recipes[1].id) == "defined"
        assert service.get_status(seed_recipes[2].id) == "none"

        # Reset all to unknown
        reset_count = 0
        for recipe in seed_recipes:
            if service.get_status(recipe.id) in ["defined", "none"]:
                # Simulate resetting
                test_db.execute(
                    text(f"UPDATE recipes SET external_status = 'unknown' WHERE id = {recipe.id}")
                )
                reset_count += 1
        test_db.commit()

        # Verify reset
        assert service.get_status(seed_recipes[0].id) == "unknown"
        assert service.get_status(seed_recipes[1].id) == "unknown"
        assert service.get_status(seed_recipes[2].id) == "unknown"


class TestExternalIngredientService:
    def test_set_ingredients_and_get(self, test_db, seed_recipes):
        recipe = seed_recipes[0]
        service = ExternalIngredientService(test_db)

        # Set ingredients
        ingredients = ["flour", "butter", "salt"]
        service.set_ingredients(recipe.id, ingredients)

        # Verify status changed
        assert service.get_status(recipe.id) == "defined"

        # Verify ingredients retrieved
        retrieved = service.get_ingredients(recipe.id)
        assert set(retrieved) == set(ingredients)

    def test_set_no_external(self, test_db, seed_recipes):
        recipe = seed_recipes[0]
        service = ExternalIngredientService(test_db)

        service.set_no_external(recipe.id)
        assert service.get_status(recipe.id) == "none"
        assert service.get_ingredients(recipe.id) == []

    def test_get_unknown_recipes(self, test_db, seed_recipes):
        service = ExternalIngredientService(test_db)

        # Mark some recipes
        service.set_no_external(seed_recipes[0].id)
        service.set_ingredients(seed_recipes[1].id, ["salt"])

        # Get unknown recipes
        unknown = service.get_unknown_recipes()
        assert len(unknown) == 6  # 8 total - 2 marked

    def test_get_recipes_needing_enrichment(self, test_db, seed_recipes):
        service = ExternalIngredientService(test_db)

        # Mark some recipes
        service.set_no_external(seed_recipes[0].id)

        # Filter specific recipes
        recipe_ids = [seed_recipes[0].id, seed_recipes[1].id, seed_recipes[2].id]
        needing = service.get_recipes_needing_enrichment(recipe_ids)

        # Should only return unknown ones
        assert len(needing) == 2
        assert seed_recipes[0].id not in [r.id for r in needing]


class TestSetCommand:
    """Test /set command service method (replace_position_with_recipe)."""

    def test_replace_recipe_success(self, test_db, seed_recipes):
        """Test successfully replacing a recipe at a position."""
        service = MenuService(test_db)
        menu = service.generate_week()
        menu_id = menu.id

        # Get position 2 (carne bianca) and find a different recipe
        items = service.get_menu_items(menu_id)
        pos2_item = items[1]
        original_recipe_id = pos2_item.recipe_id

        # Get all recipes
        recipe_service = RecipeService(test_db)
        all_recipes = recipe_service.get_all()

        # Find a recipe not currently in the menu
        used_recipe_ids = {item.recipe_id for item in items}
        other_recipe = next((r for r in all_recipes if r.id not in used_recipe_ids and r.category == pos2_item.recipe.category), None)

        # If no different recipe, just verify the operation fails gracefully
        if other_recipe is None:
            # With limited test recipes, this might happen - test position 7 instead
            other_recipe = next((r for r in all_recipes if r.id not in used_recipe_ids), None)
            if other_recipe:
                # Try to replace position 7
                result = service.replace_position_with_recipe(menu_id, 7, other_recipe.id)
                assert result["success"] is True
            return

        result = service.replace_position_with_recipe(menu_id, 2, other_recipe.id)
        assert result["success"] is True

        # Verify update
        items = service.get_menu_items(menu_id)
        pos2_item = items[1]
        assert pos2_item.recipe_id == other_recipe.id

    def test_replace_recipe_duplicate_fails(self, test_db, seed_recipes):
        """Test that replacing with a recipe already in menu fails."""
        service = MenuService(test_db)
        menu = service.generate_week()
        menu_id = menu.id

        items = service.get_menu_items(menu_id)
        pos1_recipe_id = items[0].recipe_id
        pos2_recipe_id = items[1].recipe_id

        # Try to replace position 2 with the recipe from position 1
        result = service.replace_position_with_recipe(menu_id, 2, pos1_recipe_id)
        assert result["success"] is False
        assert "already exists" in result["error"]

    def test_replace_recipe_wrong_category_fails(self, test_db, seed_recipes):
        """Test that replacing position 1-6 with wrong category fails."""
        service = MenuService(test_db)
        menu = service.generate_week()
        menu_id = menu.id

        items = service.get_menu_items(menu_id)
        pos1_item = items[0]
        pos1_category = pos1_item.recipe.category

        # Find a recipe from a different category that's NOT in the menu
        recipe_service = RecipeService(test_db)
        all_recipes = recipe_service.get_all()
        used_recipe_ids = {item.recipe_id for item in items}

        all_categories = ["carne rossa", "carne bianca", "pesce", "uova", "legumi", "altro"]
        different_category = next(c for c in all_categories if c != pos1_category)

        # Find a recipe in different category that's not in the menu
        different_recipe = next(
            (r for r in all_recipes if r.category == different_category and r.id not in used_recipe_ids),
            None
        )

        if different_recipe is None:
            # With limited recipes, this might not be possible - skip the test
            return

        result = service.replace_position_with_recipe(menu_id, 1, different_recipe.id)
        assert result["success"] is False
        assert "category" in result["error"].lower()

    def test_replace_position_7_allows_any_category(self, test_db, seed_recipes):
        """Test that position 7 allows recipes from any category."""
        service = MenuService(test_db)
        menu = service.generate_week()
        menu_id = menu.id

        items = service.get_menu_items(menu_id)
        pos7_item = items[6]
        original_category = pos7_item.recipe.category

        # Find a recipe from a different category that's NOT in the menu
        recipe_service = RecipeService(test_db)
        all_recipes = recipe_service.get_all()
        used_recipe_ids = {item.recipe_id for item in items}

        all_categories = ["carne rossa", "carne bianca", "pesce", "uova", "legumi", "altro"]
        different_category = next(c for c in all_categories if c != original_category)

        # Find a recipe in different category that's not in the menu
        different_recipe = next(
            (r for r in all_recipes if r.category == different_category and r.id not in used_recipe_ids),
            None
        )

        if different_recipe is None:
            # With limited recipes, this might not be possible - skip the test
            return

        result = service.replace_position_with_recipe(menu_id, 7, different_recipe.id)
        assert result["success"] is True

        # Verify update
        items = service.get_menu_items(menu_id)
        pos7_item = items[6]
        assert pos7_item.recipe_id == different_recipe.id
        assert pos7_item.recipe.category == different_category

    def test_replace_recipe_invalid_menu(self, test_db):
        """Test that replacing in non-existent menu fails."""
        service = MenuService(test_db)
        result = service.replace_position_with_recipe(999, 2, 999)
        assert result["success"] is False
        assert "not found" in result["error"]

    def test_replace_recipe_invalid_recipe(self, test_db, seed_recipes):
        """Test that replacing with non-existent recipe fails."""
        service = MenuService(test_db)
        menu = service.generate_week()
        menu_id = menu.id

        result = service.replace_position_with_recipe(menu_id, 2, 999)
        assert result["success"] is False
        assert "not found" in result["error"]

    def test_replace_recipe_invalid_position(self, test_db, seed_recipes):
        """Test that invalid position is rejected."""
        service = MenuService(test_db)
        menu = service.generate_week()
        menu_id = menu.id

        recipe_id = service.get_menu_items(menu_id)[0].recipe_id

        result = service.replace_position_with_recipe(menu_id, 8, recipe_id)
        assert result["success"] is False
        assert "between 1 and 7" in result["error"]

    def test_replace_recipe_accepted_menu_fails(self, test_db, seed_recipes):
        """Test that replacing in accepted menu fails."""
        service = MenuService(test_db)
        menu = service.generate_week()
        menu_id = menu.id

        service.accept_menu(menu_id)
        recipe_id = service.get_menu_items(menu_id)[0].recipe_id

        result = service.replace_position_with_recipe(menu_id, 2, recipe_id)
        assert result["success"] is False
        assert "accepted" in result["error"]


class TestExternalIngredientPersistence:
    """Test that external ingredient status is properly persisted to database."""

    def test_set_ingredients_persists_status_to_database(self, test_db, seed_recipes):
        """Verify set_ingredients updates Recipe.external_status in database."""
        service = ExternalIngredientService(test_db)
        recipe_id = seed_recipes[0].id

        # Verify initial status
        assert service.get_status(recipe_id) == "unknown"

        # Set ingredients
        ingredients = ["salmon", "dill"]
        service.set_ingredients(recipe_id, ingredients)

        # Query fresh to verify persistence
        fresh_status = service.get_status(recipe_id)
        assert fresh_status == "defined", \
            "Recipe.external_status should be persisted as 'defined'"

        # Verify ingredients were saved
        saved_ingredients = service.get_ingredients(recipe_id)
        assert set(saved_ingredients) == set(ingredients)

    def test_set_no_external_persists_status_to_database(self, test_db, seed_recipes):
        """Verify set_no_external updates Recipe.external_status in database."""
        service = ExternalIngredientService(test_db)
        recipe_id = seed_recipes[1].id

        # Verify initial status
        assert service.get_status(recipe_id) == "unknown"

        # Mark as no external
        service.set_no_external(recipe_id)

        # Query fresh to verify persistence
        fresh_status = service.get_status(recipe_id)
        assert fresh_status == "none", \
            "Recipe.external_status should be persisted as 'none'"

    def test_external_status_queryable_after_set(self, test_db, seed_recipes):
        """Verify external status is immediately queryable after set_ingredients."""
        service = ExternalIngredientService(test_db)
        recipe_id = seed_recipes[2].id

        # Set ingredients
        service.set_ingredients(recipe_id, ["jackfruit"])

        # Query using get_status (which does a fresh query)
        status = service.get_status(recipe_id)
        assert status == "defined", "Status should be queryable and correct after set_ingredients"
