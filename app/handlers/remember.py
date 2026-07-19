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
        from app.services.menu_service import MenuService

        menu_service = MenuService(session)
        shopping_service = ShoppingReminderService(session)
        external_service = ExternalIngredientService(session)

        # Get the most recent accepted menu
        recent_menus = menu_service.get_recent_accepted_menus(limit=1)
        current_menu_id = recent_menus[0].id if recent_menus else None

        # If no args, just show the current list
        if not context.args:
            # Collect external ingredients only from current menu's recipes
            recipe_ingredients = []
            if current_menu_id:
                items = menu_service.get_menu_items(current_menu_id)
                for item in items:
                    if external_service.get_status(item.recipe_id) == "defined":
                        recipe_ingredients.extend(external_service.get_ingredients(item.recipe_id))

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
        added = shopping_service.add_reminders(items)

        # Get updated consolidated list (only from current menu)
        recipe_ingredients = []
        if current_menu_id:
            items = menu_service.get_menu_items(current_menu_id)
            for item in items:
                if external_service.get_status(item.recipe_id) == "defined":
                    recipe_ingredients.extend(external_service.get_ingredients(item.recipe_id))

        reminders = shopping_service.get_active_reminders()
        consolidated = recipe_ingredients + reminders

        # Show consolidated list
        text = format_consolidated_shopping_list(consolidated)
        await update.message.reply_text(text)

    finally:
        session.close()
