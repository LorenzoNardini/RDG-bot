from telegram import Update
from telegram.ext import ContextTypes
from app.database.db import get_session
from app.services.recipe_service import RecipeService
from app.utils.formatting import format_recipe_list

CATEGORIES = ["carne rossa", "carne bianca", "pesce", "uova", "legumi", "altro"]


async def list_recipes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /list command.
    Usage: /list or /list <category>
    Examples: /list, /list pesce
    """
    session = get_session()
    try:
        recipe_service = RecipeService(session)

        # Check if category filter is provided
        if context.args:
            category = " ".join(context.args).lower()
            if category not in CATEGORIES:
                await update.message.reply_text(
                    f"❌ Invalid category: {category}\n"
                    f"Valid categories: {', '.join(CATEGORIES)}",
                    parse_mode="Markdown"
                )
                return
            recipes = recipe_service.get_by_category(category)
        else:
            recipes = recipe_service.get_all()

        if not recipes:
            await update.message.reply_text("No recipes found.")
            return

        menu_text = format_recipe_list(recipes)
        await update.message.reply_text(menu_text, parse_mode="Markdown")

    finally:
        session.close()
