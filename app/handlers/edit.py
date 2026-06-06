from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from app.database.db import get_session
from app.services.recipe_service import RecipeService
from app.services.external_service import ExternalIngredientService

CATEGORIES = ["carne rossa", "carne bianca", "pesce", "uova", "legumi", "altro"]


async def edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /edit command - start recipe editing."""
    if not context.args:
        await update.message.reply_text(
            'Usage: /edit "Recipe Name"\nExample: /edit "Pasta Carbonara"'
        )
        return

    recipe_name = " ".join(context.args).strip('"')
    session = get_session()
    try:
        recipe_service = RecipeService(session)
        recipe = recipe_service.get_by_name(recipe_name)

        if not recipe:
            await update.message.reply_text(f'Recipe not found: {recipe_name}')
            return

        # Store recipe in context
        context.user_data["edit_recipe_id"] = recipe.id
        context.user_data["edit_recipe_name"] = recipe.name

        # Show edit options
        keyboard = [
            [InlineKeyboardButton("Name", callback_data="edit_name")],
            [InlineKeyboardButton("Category", callback_data="edit_category")],
            [InlineKeyboardButton("Needs Side?", callback_data="edit_needs_side")],
            [InlineKeyboardButton("Suggested Side", callback_data="edit_suggested_side")],
            [InlineKeyboardButton("External Ingredients", callback_data="edit_external")],
            [InlineKeyboardButton("Cancel", callback_data="edit_cancel")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"Editing: {recipe.name}\n\nWhat would you like to edit?",
            reply_markup=reply_markup
        )

    finally:
        session.close()


async def edit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle edit field selection via callback."""
    query = update.callback_query
    await query.answer()

    choice = query.data
    recipe_id = context.user_data.get("edit_recipe_id")

    if choice == "edit_cancel":
        await query.edit_message_text("Cancelled.")
        context.user_data["edit_recipe_id"] = None
        context.user_data["edit_field"] = None
        return

    context.user_data["edit_field"] = choice

    prompts = {
        "edit_name": "Enter new recipe name:",
        "edit_category": f"Enter new category:\n" + "\n".join([f"• {c}" for c in CATEGORIES]),
        "edit_needs_side": "Does it need a side dish? (yes/no)",
        "edit_suggested_side": "Enter suggested side (or 'none' to clear):",
        "edit_external": "Enter external ingredients (comma-separated), or 'none' to clear:",
    }

    await query.edit_message_text(prompts.get(choice, "Enter value:"))


async def edit_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle value input for editing."""
    value = update.message.text.strip()
    recipe_id = context.user_data.get("edit_recipe_id")
    field = context.user_data.get("edit_field")

    if not recipe_id or not field:
        await update.message.reply_text("Edit session expired. Try /edit again.")
        return

    session = get_session()
    try:
        recipe_service = RecipeService(session)
        recipe = recipe_service.get_by_id(recipe_id)

        if not recipe:
            await update.message.reply_text("Recipe not found.")
            return

        if field == "edit_name":
            existing = recipe_service.get_by_name(value)
            if existing and existing.id != recipe_id:
                await update.message.reply_text(f"Recipe '{value}' already exists.")
                return
            recipe.name = value
            session.commit()
            await update.message.reply_text(f"Updated: {value}")

        elif field == "edit_category":
            if value.lower() not in CATEGORIES:
                await update.message.reply_text(f"Invalid. Valid: {', '.join(CATEGORIES)}")
                return
            recipe.category = value.lower()
            session.commit()
            await update.message.reply_text(f"Category: {value}")

        elif field == "edit_needs_side":
            needs = value.lower() in ["yes", "sì", "s", "true", "1"]
            recipe.needs_side = needs
            session.commit()
            await update.message.reply_text(f"Needs side: {'Yes' if needs else 'No'}")

        elif field == "edit_suggested_side":
            if value.lower() in ["none", "nessuno", "-"]:
                recipe.suggested_side = None
                session.commit()
                await update.message.reply_text("Suggested side cleared.")
            else:
                recipe.suggested_side = value
                session.commit()
                await update.message.reply_text(f"Suggested side: {value}")

        elif field == "edit_external":
            external_service = ExternalIngredientService(session)
            if value.lower() in ["none", "nessuno", "-"]:
                external_service.set_no_external(recipe_id)
                await update.message.reply_text("Marked as no external ingredients.")
            else:
                ingredients = [ing.strip() for ing in value.split(",") if ing.strip()]
                external_service.set_ingredients(recipe_id, ingredients)
                ing_text = ", ".join(ingredients)
                await update.message.reply_text(f"External ingredients: {ing_text}")

        context.user_data["edit_recipe_id"] = None
        context.user_data["edit_field"] = None

    finally:
        session.close()
