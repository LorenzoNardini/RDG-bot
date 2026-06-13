from telegram import Update
from telegram.ext import ContextTypes
from app.database.db import get_session
from app.services.shopping_service import ShoppingReminderService
from app.services.external_service import ExternalIngredientService


async def bought(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /bought command - mark items as bought.
    Clears shopping reminders and resets recipe external status to unknown.
    """
    session = get_session()
    try:
        shopping_service = ShoppingReminderService(session)
        external_service = ExternalIngredientService(session)

        # Count items before clearing
        reminders_count = shopping_service.count_active()

        # Count recipes with external ingredient info
        from app.models.models import Recipe
        recipes_with_info = 0
        for recipe in session.query(Recipe).all():
            status = external_service.get_status(recipe.id)
            if status in ["defined", "none"]:
                recipes_with_info += 1

        # Clear reminders
        shopping_service.clear_reminders()

        # Reset all recipes to unknown
        for recipe in session.query(Recipe).all():
            status = external_service.get_status(recipe.id)
            if status in ["defined", "none"]:
                recipe.external_status = "unknown"
        session.commit()

        # Show confirmation
        total_cleared = reminders_count + recipes_with_info
        if total_cleared == 0:
            await update.message.reply_text("Nothing to mark as bought!")
        else:
            await update.message.reply_text(
                f"✅ Marked {total_cleared} items as bought.\n\n"
                f"Your shopping list is now clear.\n"
                f"Next time you /accept a menu, we'll ask about ingredients again."
            )

    finally:
        session.close()
