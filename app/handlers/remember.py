from telegram import Update
from telegram.ext import ContextTypes
from app.database.db import get_session
from app.services.shopping_service import ShoppingReminderService


async def remember(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /remember command - add shopping reminders.
    Usage: /remember olive oil
    Multiple: /remember coffee beans, batteries, olive oil
    """
    if not context.args:
        await update.message.reply_text(
            "Usage:\n"
            "• Single: `/remember olive oil`\n"
            "• Multiple: `/remember coffee beans, batteries, olive oil`"
        )
        return

    items_text = " ".join(context.args)
    items = [item.strip() for item in items_text.split(",") if item.strip()]

    if not items:
        await update.message.reply_text("Please provide at least one item.")
        return

    session = get_session()
    try:
        service = ShoppingReminderService(session)
        added = service.add_reminders(items)

        if added == 0:
            await update.message.reply_text(
                "Items already in your reminder list:\n" +
                "\n".join([f"  • {item}" for item in items])
            )
        else:
            await update.message.reply_text(
                f"Added to shopping reminders:\n" +
                "\n".join([f"  • {item}" for item in items[:added]])
            )

    finally:
        session.close()
