from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters
from app.database.db import get_session
from app.services.recipe_service import RecipeService
from app.services.external_service import ExternalIngredientService

CATEGORIES = ["carne rossa", "carne bianca", "pesce", "uova", "legumi", "altro"]
CHOOSE_FIELD, ENTER_VALUE = range(2)


async def edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /edit command - start recipe editing."""
    if not context.args:
        await update.message.reply_text(
            'Usage: /edit "Recipe Name"\nExample: /edit "Pasta Carbonara"'
        )
        return ConversationHandler.END

    recipe_name = " ".join(context.args).strip('"')
    session = get_session()
    try:
        recipe_service = RecipeService(session)
        recipe = recipe_service.get_by_name(recipe_name)

        if not recipe:
            await update.message.reply_text(f'Recipe not found: {recipe_name}')
            return ConversationHandler.END

        # Store recipe in context
        context.user_data["edit_recipe_id"] = recipe.id
        context.user_data["edit_recipe_name"] = recipe.name

        # Show numbered menu
        menu = (
            f"Editing: {recipe.name}\n\n"
            f"What would you like to edit?\n\n"
            f"1. Name\n"
            f"2. Category\n"
            f"3. Needs Side?\n"
            f"4. Suggested Side\n"
            f"5. External Ingredients\n\n"
            f"Reply with the number (1-5):"
        )
        await update.message.reply_text(menu)
        return CHOOSE_FIELD

    finally:
        session.close()


async def edit_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle field selection by number."""
    choice_text = update.message.text.strip()
    recipe_id = context.user_data.get("edit_recipe_id")

    if not recipe_id:
        return ConversationHandler.END

    try:
        choice = int(choice_text)
    except ValueError:
        await update.message.reply_text("Please reply with a number (1-5).")
        return CHOOSE_FIELD

    if choice == 1:
        context.user_data["edit_field"] = "name"
        await update.message.reply_text("Enter new recipe name:")
        return ENTER_VALUE
    elif choice == 2:
        context.user_data["edit_field"] = "category"
        categories = "\n".join([f"  • {c}" for c in CATEGORIES])
        await update.message.reply_text(f"Enter new category:\n{categories}")
        return ENTER_VALUE
    elif choice == 3:
        context.user_data["edit_field"] = "needs_side"
        await update.message.reply_text("Does it need a side dish? (yes/no)")
        return ENTER_VALUE
    elif choice == 4:
        context.user_data["edit_field"] = "suggested_side"
        await update.message.reply_text("Enter suggested side (or 'none' to clear):")
        return ENTER_VALUE
    elif choice == 5:
        context.user_data["edit_field"] = "external"
        await update.message.reply_text("Enter external ingredients (comma-separated), or 'none' to clear:")
        return ENTER_VALUE
    else:
        await update.message.reply_text("Invalid choice. Please enter 1-5.")
        return CHOOSE_FIELD


async def edit_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle value input for editing."""
    value = update.message.text.strip()
    recipe_id = context.user_data.get("edit_recipe_id")
    field = context.user_data.get("edit_field")

    if not recipe_id or not field:
        return

    session = get_session()
    try:
        recipe_service = RecipeService(session)
        recipe = recipe_service.get_by_id(recipe_id)

        if not recipe:
            await update.message.reply_text("Recipe not found.")
            return

        if field == "name":
            existing = recipe_service.get_by_name(value)
            if existing and existing.id != recipe_id:
                await update.message.reply_text(f"Recipe '{value}' already exists.")
                return
            recipe.name = value
            session.commit()
            await update.message.reply_text(f"Updated: {value}")

        elif field == "category":
            if value.lower() not in CATEGORIES:
                await update.message.reply_text(f"Invalid. Valid: {', '.join(CATEGORIES)}")
                return
            recipe.category = value.lower()
            session.commit()
            await update.message.reply_text(f"Category: {value}")

        elif field == "needs_side":
            needs = value.lower() in ["yes", "sì", "s", "true", "1"]
            recipe.needs_side = needs
            session.commit()
            await update.message.reply_text(f"Needs side: {'Yes' if needs else 'No'}")

        elif field == "suggested_side":
            if value.lower() in ["none", "nessuno", "-"]:
                recipe.suggested_side = None
                session.commit()
                await update.message.reply_text("Suggested side cleared.")
            else:
                recipe.suggested_side = value
                session.commit()
                await update.message.reply_text(f"Suggested side: {value}")

        elif field == "external":
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
        return ConversationHandler.END

    finally:
        session.close()


def get_edit_handler():
    """Return ConversationHandler for /edit command."""
    return ConversationHandler(
        entry_points=[CommandHandler("edit", edit)],
        states={
            CHOOSE_FIELD: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_choice)],
            ENTER_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_value)],
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: c.user_data.update({"edit_recipe_id": None, "edit_field": None}))],
    )
