import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.models import Base, Recipe, WeeklyMenu, WeeklyMenuItem, ExternalIngredient
from telegram import Update, User, Chat, Message


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
    """Seed test recipes across all categories."""
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


def create_mock_update(text, args=None):
    """Create a mock Telegram Update object."""
    user = MagicMock(spec=User)
    user.id = 123
    chat = MagicMock(spec=Chat)
    message = MagicMock(spec=Message)
    message.text = text
    update = MagicMock(spec=Update)
    update.message = message
    update.effective_user = user
    return update, message


@pytest.mark.asyncio
class TestRememberHandler:
    async def test_remember_shows_consolidated_shopping_list(self, test_db, seed_recipes):
        """Test that /remember displays consolidated shopping list."""
        from app.handlers.remember import remember
        from app.services.external_service import ExternalIngredientService
        from app.services.shopping_service import ShoppingReminderService

        # Setup: add recipe ingredients and reminders
        external_service = ExternalIngredientService(test_db)
        external_service.set_ingredients(seed_recipes[0].id, ["flour", "butter"])

        shopping_service = ShoppingReminderService(test_db)
        shopping_service.add_reminders(["olive oil"])

        # Create mock update and context
        update, message = create_mock_update("/remember", ["olive oil", "coffee"])
        context = MagicMock()
        context.args = ["olive oil", "coffee"]
        context.user_data = {}

        with patch("app.handlers.remember.get_session", return_value=test_db):
            await remember(update, context)

        # Verify that a message was sent (contains consolidated list)
        message.reply_text.assert_called()
        call_args = message.reply_text.call_args[0][0]
        assert "🛒" in call_args
        assert "Remember to buy" in call_args or "remember to buy" in call_args.lower()

    async def test_remember_no_items_shows_message(self, test_db):
        """Test that /remember with no items shows appropriate message."""
        from app.handlers.remember import remember

        update, message = create_mock_update("/remember", [])
        context = MagicMock()
        context.args = []
        context.user_data = {}

        with patch("app.handlers.remember.get_session", return_value=test_db):
            await remember(update, context)

        message.reply_text.assert_called()


@pytest.mark.asyncio
class TestBoughtHandler:
    async def test_bought_clears_reminders(self, test_db):
        """Test that /bought clears all shopping reminders."""
        from app.handlers.bought import bought
        from app.services.shopping_service import ShoppingReminderService

        # Setup reminders
        service = ShoppingReminderService(test_db)
        service.add_reminders(["olive oil", "coffee"])

        update, message = create_mock_update("/bought", [])
        context = MagicMock()
        context.args = []
        context.user_data = {}

        with patch("app.handlers.bought.get_session", return_value=test_db):
            await bought(update, context)

        # Verify reminders were cleared
        assert service.count_active() == 0
        message.reply_text.assert_called()

    async def test_bought_shows_confirmation(self, test_db):
        """Test that /bought shows what was cleared."""
        from app.handlers.bought import bought
        from app.services.shopping_service import ShoppingReminderService

        service = ShoppingReminderService(test_db)
        service.add_reminders(["olive oil"])

        update, message = create_mock_update("/bought", [])
        context = MagicMock()
        context.args = []
        context.user_data = {}

        with patch("app.handlers.bought.get_session", return_value=test_db):
            await bought(update, context)

        message.reply_text.assert_called()
        call_args = message.reply_text.call_args[0][0]
        # Should indicate items were marked as bought
        assert "bought" in call_args.lower() or "cleared" in call_args.lower()


@pytest.mark.asyncio
class TestListHandler:
    async def test_list_single_word_category(self, test_db, seed_recipes):
        """Test /list with single-word category like 'pesce'."""
        from app.handlers.list_ import list_recipes

        update, message = create_mock_update("/list pesce", ["pesce"])
        context = MagicMock()
        context.args = ["pesce"]

        with patch("app.handlers.list_.get_session", return_value=test_db):
            await list_recipes(update, context)

        message.reply_text.assert_called_once()
        call_args = message.reply_text.call_args[0][0]
        assert "Branzino al Forno" in call_args

    async def test_list_multi_word_category(self, test_db, seed_recipes):
        """Test /list with multi-word category like 'carne bianca' - BUG FIX."""
        from app.handlers.list_ import list_recipes

        update, message = create_mock_update("/list carne bianca", ["carne", "bianca"])
        context = MagicMock()
        context.args = ["carne", "bianca"]

        with patch("app.handlers.list_.get_session", return_value=test_db):
            await list_recipes(update, context)

        message.reply_text.assert_called_once()
        call_args = message.reply_text.call_args[0][0]
        assert "Petto di Pollo" in call_args

    async def test_list_invalid_category(self, test_db, seed_recipes):
        """Test /list with invalid category."""
        from app.handlers.list_ import list_recipes

        update, message = create_mock_update("/list invalid", ["invalid"])
        context = MagicMock()
        context.args = ["invalid"]

        with patch("app.handlers.list_.get_session", return_value=test_db):
            await list_recipes(update, context)

        message.reply_text.assert_called_once()
        call_args = message.reply_text.call_args[0][0]
        assert "Invalid category" in call_args


@pytest.mark.asyncio
class TestHistoryHandler:
    async def test_history_no_args_defaults_to_1(self, test_db, seed_recipes):
        """Test /history with no args shows last 1 menu (default)."""
        from app.handlers.history import history
        from app.services.menu_service import MenuService

        # Create and accept 3 menus
        menu_service = MenuService(test_db)
        for _ in range(3):
            menu = menu_service.generate_week()
            menu_service.accept_menu(menu.id)

        update, message = create_mock_update("/history", [])
        context = MagicMock()
        context.args = []
        context.user_data = {}

        with patch("app.handlers.history.get_session", return_value=test_db):
            await history(update, context)

        message.reply_text.assert_called()
        call_args = message.reply_text.call_args[0][0]
        # Should show "Menu #1" only (last 1)
        assert "Menu #1" in call_args
        assert "Menu #2" not in call_args

    async def test_history_with_number_arg(self, test_db, seed_recipes):
        """Test /history <n> shows last n menus."""
        from app.handlers.history import history
        from app.services.menu_service import MenuService

        # Create and accept 3 menus
        menu_service = MenuService(test_db)
        for _ in range(3):
            menu = menu_service.generate_week()
            menu_service.accept_menu(menu.id)

        update, message = create_mock_update("/history 2", ["2"])
        context = MagicMock()
        context.args = ["2"]
        context.user_data = {}

        with patch("app.handlers.history.get_session", return_value=test_db):
            await history(update, context)

        message.reply_text.assert_called()
        call_args = message.reply_text.call_args[0][0]
        # Should show "Menu #1" and "Menu #2" (last 2)
        assert "Menu #1" in call_args
        assert "Menu #2" in call_args

    async def test_history_invalid_number(self, test_db):
        """Test /history with invalid number shows error."""
        from app.handlers.history import history

        update, message = create_mock_update("/history invalid", ["invalid"])
        context = MagicMock()
        context.args = ["invalid"]
        context.user_data = {}

        with patch("app.handlers.history.get_session", return_value=test_db):
            await history(update, context)

        message.reply_text.assert_called()
        call_args = message.reply_text.call_args[0][0]
        assert "valid number" in call_args.lower()

    async def test_history_negative_number(self, test_db):
        """Test /history with negative number shows error."""
        from app.handlers.history import history

        update, message = create_mock_update("/history -1", ["-1"])
        context = MagicMock()
        context.args = ["-1"]
        context.user_data = {}

        with patch("app.handlers.history.get_session", return_value=test_db):
            await history(update, context)

        message.reply_text.assert_called()
        call_args = message.reply_text.call_args[0][0]
        assert "positive" in call_args.lower()


@pytest.mark.asyncio
class TestExternalHandler:
    async def test_external_single_command(self, test_db, seed_recipes):
        """Test /external with single ingredient."""
        from app.handlers.external import external_cmd
        from app.services.external_service import ExternalIngredientService

        # Setup enrichment
        recipe = seed_recipes[0]
        update, message = create_mock_update(
            "/external 1 flour, butter",
            ["1", "flour,", "butter"]
        )
        context = MagicMock()
        context.args = ["1", "flour,", "butter"]
        context.user_data = {"enrichment_recipes": {1: recipe.id}}

        with patch("app.handlers.external.get_session", return_value=test_db):
            await external_cmd(update, context)

        message.reply_text.assert_called()
        # Verify the recipe was updated
        service = ExternalIngredientService(test_db)
        ingredients = service.get_ingredients(recipe.id)
        assert "flour" in ingredients
        assert "butter" in ingredients

    async def test_external_with_slash_stops_parsing(self, test_db, seed_recipes):
        """Test that /external stops parsing at next slash - BUG FIX."""
        from app.handlers.external import external_cmd

        recipe = seed_recipes[0]
        update, message = create_mock_update(
            "/external 1 flour, butter /external 2 salt",
            ["1", "flour,", "butter", "/external", "2", "salt"]
        )
        context = MagicMock()
        context.args = ["1", "flour,", "butter", "/external", "2", "salt"]
        context.user_data = {"enrichment_recipes": {1: recipe.id}}

        with patch("app.handlers.external.get_session", return_value=test_db):
            await external_cmd(update, context)

        # Should only parse up to the slash
        from app.services.external_service import ExternalIngredientService
        service = ExternalIngredientService(test_db)
        ingredients = service.get_ingredients(recipe.id)
        # Should have flour, butter but NOT the slash or subsequent command
        assert "flour" in ingredients
        assert "butter" in ingredients
        assert "/external" not in " ".join(ingredients)
        assert "salt" not in " ".join(ingredients)


@pytest.mark.asyncio
class TestRerollHandler:
    async def test_reroll_position_maintains_category(self, test_db, seed_recipes):
        """Test that /reroll <position> maintains category - BUG FIX."""
        from app.handlers.reroll import reroll
        from app.services.menu_service import MenuService

        # Setup a menu
        menu_service = MenuService(test_db)
        menu = menu_service.generate_week()
        menu_id = menu.id

        # Get the original category of position 1
        items = menu_service.get_menu_items(menu_id)
        original_category = items[0].recipe.category

        update, message = create_mock_update("/reroll 1", ["1"])
        context = MagicMock()
        context.args = ["1"]
        context.user_data = {"pending_menu_id": menu_id}

        with patch("app.handlers.reroll.get_session", return_value=test_db):
            await reroll(update, context)

        # Verify the category is maintained (use fresh query)
        menu_service = MenuService(test_db)
        items = menu_service.get_menu_items(menu_id)
        new_item = items[0]
        assert new_item.recipe.category == original_category

    async def test_reroll_category_changes_recipe(self, test_db, seed_recipes):
        """Test that /reroll <category> works correctly."""
        from app.handlers.reroll import reroll

        # Setup a menu
        from app.services.menu_service import MenuService
        menu_service = MenuService(test_db)
        menu = menu_service.generate_week()
        menu_id = menu.id

        update, message = create_mock_update("/reroll pesce", ["pesce"])
        context = MagicMock()
        context.args = ["pesce"]
        context.user_data = {"pending_menu_id": menu_id}

        with patch("app.handlers.reroll.get_session", return_value=test_db):
            await reroll(update, context)

        # Should show success message
        message.reply_text.assert_called()
        call_args = message.reply_text.call_args[0][0]
        assert "regenerated" in call_args.lower() or "Pesce" in call_args
