from telegram import Update
from telegram.ext import ContextTypes
from app.database.db import get_session
from app.services.shopping_list_service import ShoppingListService
from app.utils.formatting import format_consolidated_shopping_list


async def remember(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /remember command - add shopping reminders and show shopping list.
    Usage: /remember olive oil
    Multiple: /remember coffee beans, batteries, olive oil
    With no args: show current shopping list
    """
    session = get_session()
    try:
        shopping_list_service = ShoppingListService(session)

        # If no args, just show the current list
        if not context.args:
            items = shopping_list_service.get_all_items()
            text = format_consolidated_shopping_list(items)
            await update.message.reply_text(text)
            return

        # Parse items to add
        items_text = " ".join(context.args)
        items = [item.strip() for item in items_text.split(",") if item.strip()]

        if not items:
            await update.message.reply_text("Please provide at least one item.")
            return

        # Add reminders to shopping list
        for item in items:
            shopping_list_service.add_reminder(item)

        # Show updated shopping list
        all_items = shopping_list_service.get_all_items()
        text = format_consolidated_shopping_list(all_items)
        await update.message.reply_text(text)

    finally:
        session.close()
