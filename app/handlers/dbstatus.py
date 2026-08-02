from telegram import Update
from telegram.ext import ContextTypes
from app.database.db import get_session
from app.models.models import Recipe, ExternalIngredient, ShoppingListItem

async def dbstatus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /dbstatus command (admin only).
    Shows the current state of the database for diagnostics.
    """
    session = get_session()
    try:
        # Count recipes by status
        total_recipes = session.query(Recipe).count()
        unknown = session.query(Recipe).filter(Recipe.external_status == "unknown").count()
        none_status = session.query(Recipe).filter(Recipe.external_status == "none").count()
        defined = session.query(Recipe).filter(Recipe.external_status == "defined").count()

        # Count external ingredients
        total_ingredients = session.query(ExternalIngredient).count()

        # Count active shopping list items
        shopping_items = session.query(ShoppingListItem).count()

        # Build status message
        msg = "🔍 *Database Status*\n\n"
        msg += f"*Recipes:*\n"
        msg += f"  Total: {total_recipes}\n"
        msg += f"  Status unknown: {unknown}\n"
        msg += f"  Status none: {none_status}\n"
        msg += f"  Status defined: {defined}\n\n"
        msg += f"*External Ingredients:*\n"
        msg += f"  Total records: {total_ingredients}\n\n"
        msg += f"*Shopping List:*\n"
        msg += f"  Active items: {shopping_items}\n"

        await update.message.reply_text(msg, parse_mode="Markdown")

    finally:
        session.close()
