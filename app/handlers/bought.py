from telegram import Update
from telegram.ext import ContextTypes
from app.database.db import get_session
from app.services.shopping_service import ShoppingReminderService


async def bought(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /bought command - mark shopping reminders as bought.
    Only clears temporary shopping reminders added via /remember.
    Preserves recipe-specific external ingredient status.
    """
    session = get_session()
    try:
        shopping_service = ShoppingReminderService(session)

        # Count items before clearing
        reminders_count = shopping_service.count_active()

        # Clear only shopping reminders (temporary items)
        shopping_service.clear_reminders()

        # Show confirmation
        if reminders_count == 0:
            await update.message.reply_text("Nothing to mark as bought!")
        else:
            await update.message.reply_text(
                f"✅ Marked {reminders_count} items as bought.\n\n"
                f"Your shopping list is now clear."
            )

    finally:
        session.close()
