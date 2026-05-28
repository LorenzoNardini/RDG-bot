from telegram import Update
from telegram.ext import ContextTypes
from app.database.db import get_session
from app.services.external_service import ExternalIngredientService


async def external_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /external command.
    Usage: /external <number> ingredient1, ingredient2, ingredient3
    Example: /external 1 salmon fillet, dill
    """
    session = get_session()
    try:
        # Parse arguments
        if not context.args or len(context.args) < 2:
            await update.message.reply_text(
                "Usage: /external <number> ingredient1, ingredient2, ...\n"
                "Example: /external 1 salmon fillet, dill",
                parse_mode="Markdown"
            )
            return

        try:
            position = int(context.args[0])
        except ValueError:
            await update.message.reply_text(
                f"Invalid position: {context.args[0]}. Use a number.",
                parse_mode="Markdown"
            )
            return

        # Get enrichment recipes mapping
        enrichment_recipes = context.user_data.get("enrichment_recipes", {})
        if position not in enrichment_recipes:
            await update.message.reply_text(
                f"Position {position} not found in current enrichment. Use /fill_missing to see all.",
                parse_mode="Markdown"
            )
            return

        recipe_id = enrichment_recipes[position]

        # Parse ingredients (stop at next slash command)
        ingredients_tokens = []
        for arg in context.args[1:]:
            if arg.startswith("/"):
                break
            ingredients_tokens.append(arg)
        ingredients_text = " ".join(ingredients_tokens)
        ingredients = [ing.strip() for ing in ingredients_text.split(",") if ing.strip()]

        if not ingredients:
            await update.message.reply_text("Please provide at least one ingredient.")
            return

        # Get recipe name
        from app.services.recipe_service import RecipeService
        recipe_service = RecipeService(session)
        recipe = recipe_service.get_by_id(recipe_id)
        if not recipe:
            await update.message.reply_text("Recipe not found.")
            return

        # Save ingredients
        external_service = ExternalIngredientService(session)
        external_service.set_ingredients(recipe_id, ingredients)

        # Format confirmation
        ing_list = ", ".join(ingredients)
        await update.message.reply_text(
            f"✅ *{recipe.name}*\nExternal ingredients: {ing_list}",
            parse_mode="Markdown"
        )

        # Remove from enrichment
        del enrichment_recipes[position]
        context.user_data["enrichment_recipes"] = enrichment_recipes

        # If no more to enrich, say so
        if not enrichment_recipes:
            await update.message.reply_text("✨ All external ingredient info is now complete!")

    finally:
        session.close()


async def noexternal_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /noexternal command.
    Usage: /noexternal <number>
    Marks a recipe as having no external ingredients needed.
    """
    session = get_session()
    try:
        # Parse position
        if not context.args:
            await update.message.reply_text(
                "Usage: /noexternal <number>",
                parse_mode="Markdown"
            )
            return

        try:
            position = int(context.args[0])
        except ValueError:
            await update.message.reply_text(
                f"Invalid position: {context.args[0]}. Use a number.",
                parse_mode="Markdown"
            )
            return

        # Get enrichment recipes mapping
        enrichment_recipes = context.user_data.get("enrichment_recipes", {})
        if position not in enrichment_recipes:
            await update.message.reply_text(
                f"Position {position} not found in current enrichment.",
                parse_mode="Markdown"
            )
            return

        recipe_id = enrichment_recipes[position]

        # Get recipe name
        from app.services.recipe_service import RecipeService
        recipe_service = RecipeService(session)
        recipe = recipe_service.get_by_id(recipe_id)
        if not recipe:
            await update.message.reply_text("Recipe not found.")
            return

        # Mark as no external ingredients
        external_service = ExternalIngredientService(session)
        external_service.set_no_external(recipe_id)

        await update.message.reply_text(
            f"✅ *{recipe.name}*\nNo external ingredients needed.",
            parse_mode="Markdown"
        )

        # Remove from enrichment
        del enrichment_recipes[position]
        context.user_data["enrichment_recipes"] = enrichment_recipes

        # If no more to enrich, say so
        if not enrichment_recipes:
            await update.message.reply_text("✨ All external ingredient info is now complete!")

    finally:
        session.close()


async def skip_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /skip command.
    Dismisses the current enrichment session without blocking workflow.
    """
    context.user_data["enrichment_recipes"] = {}
    await update.message.reply_text(
        "Skipped enrichment. You can always use /fill_missing later to improve the database.",
        parse_mode="Markdown"
    )
