from telegram import Update
from telegram.ext import ContextTypes
from app.database.db import get_session
from app.services.shopping_service import ShoppingReminderService
from app.services.external_service import ExternalIngredientService
from app.utils.formatting import format_consolidated_shopping_list


async def remember(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /remember command - add shopping reminders and show consolidated list.
    Usage: /remember olive oil
    Multiple: /remember coffee beans, batteries, olive oil
    With no args: show current consolidated shopping list
    """
    session = get_session()
    try:
        # If no args, just show the current list
        if not context.args:
            shopping_service = ShoppingReminderService(session)
            external_service = ExternalIngredientService(session)

            # Collect all recipe external ingredients
            recipe_ingredients = []
            from app.models.models import Recipe
            recipes = session.query(Recipe).all()
            for recipe in recipes:
                if external_service.get_status(recipe.id) == "defined":
                    recipe_ingredients.extend(external_service.get_ingredients(recipe.id))

            # Get reminders
            reminders = shopping_service.get_active_reminders()

            # Consolidate
            consolidated = recipe_ingredients + reminders

            # Display
            text = format_consolidated_shopping_list(consolidated)
            await update.message.reply_text(text)
            return

        # Parse items to add
        items_text = " ".join(context.args)
        items = [item.strip() for item in items_text.split(",") if item.strip()]

        if not items:
            await update.message.reply_text("Please provide at least one item.")
            return

        # Add reminders
        shopping_service = ShoppingReminderService(session)
        added = shopping_service.add_reminders(items)

        # Get updated consolidated list
        external_service = ExternalIngredientService(session)
        recipe_ingredients = []
        from app.models.models import Recipe
        recipes = session.query(Recipe).all()
        for recipe in recipes:
            if external_service.get_status(recipe.id) == "defined":
                recipe_ingredients.extend(external_service.get_ingredients(recipe.id))

        reminders = shopping_service.get_active_reminders()
        consolidated = recipe_ingredients + reminders

        # Show consolidated list
        text = format_consolidated_shopping_list(consolidated)
        await update.message.reply_text(text)

    finally:
        session.close()
