from telegram import Update
from telegram.ext import ContextTypes
from app.database.db import get_session
from app.services.external_service import ExternalIngredientService
from app.utils.formatting import format_enrichment_prompt


async def fill_missing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /fill_missing command.
    Shows all recipes with unknown external ingredient status.
    Allows user to progressively enrich the database.
    """
    session = get_session()
    try:
        external_service = ExternalIngredientService(session)
        unknown_recipes = external_service.get_unknown_recipes()

        if not unknown_recipes:
            await update.message.reply_text(
                "🎉 All recipes have external ingredient information!",
                parse_mode="Markdown"
            )
            return

        # Build numbered mapping
        enrichment_recipes = {i: recipe.id for i, recipe in enumerate(unknown_recipes, 1)}
        context.user_data["enrichment_recipes"] = enrichment_recipes

        # Format and send prompt
        prompt = format_enrichment_prompt(unknown_recipes)
        await update.message.reply_text(prompt, parse_mode="Markdown")

    finally:
        session.close()
