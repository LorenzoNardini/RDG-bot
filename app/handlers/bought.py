from telegram import Update
from telegram.ext import ContextTypes
from app.database.db import get_session
from app.services.shopping_list_service import ShoppingListService


async def bought(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /bought command - clear the shopping list.
    Removes all items (external ingredients + reminders) from the active shopping list.
    External ingredient data persists in database and reappears with next menu acceptance.
    """
    session = get_session()
    try:
        shopping_list_service = ShoppingListService(session)

        # Count items before clearing
        items_count = shopping_list_service.count_items()

        # Clear entire shopping list
        shopping_list_service.clear_all()

        # Show confirmation
        if items_count == 0:
            await update.message.reply_text("Nothing to mark as bought!")
        else:
            await update.message.reply_text(
                f"✅ Marked {items_count} items as bought.\n\n"
                f"Your shopping list is now clear."
            )

    finally:
        session.close()
