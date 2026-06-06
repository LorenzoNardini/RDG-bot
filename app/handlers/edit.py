from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, MessageHandler, CommandHandler, filters
from app.database.db import get_session
from app.services.recipe_service import RecipeService
from app.services.external_service import ExternalIngredientService

# States
CHOOSE_FIELD, ENTER_VALUE = range(2)

CATEGORIES = ["carne rossa", "carne bianca", "pesce", "uova", "legumi", "altro"]


async def edit_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start /edit command - ask for recipe name."""
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

        # Store recipe in context (DON'T store session - create new ones in handlers)
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
            f"Editing: *{recipe.name}*\n\nWhat would you like to edit?",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

        return CHOOSE_FIELD

    except Exception as e:
        await update.message.reply_text(f"Error: {e}")
        return ConversationHandler.END
    finally:
        session.close()


async def handle_field_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle field selection."""
    query = update.callback_query
    await query.answer()

    choice = query.data

    if choice == "edit_cancel":
        await query.edit_message_text("Editing cancelled.")
        return ConversationHandler.END

    context.user_data["edit_field"] = choice

    if choice == "edit_name":
        await query.edit_message_text("Enter new recipe name:")
    elif choice == "edit_category":
        categories_list = "\n".join([f"• {c}" for c in CATEGORIES])
        await query.edit_message_text(f"Enter new category:\n{categories_list}")
    elif choice == "edit_needs_side":
        await query.edit_message_text("Does it need a side dish? (yes/no)")
    elif choice == "edit_suggested_side":
        await query.edit_message_text("Enter suggested side (or 'none' to clear):")
    elif choice == "edit_external":
        await query.edit_message_text("Enter external ingredients (comma-separated), or 'none' to clear:")

    return ENTER_VALUE


async def handle_value_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle value entry for the selected field."""
    value = update.message.text.strip()
    recipe_id = context.user_data.get("edit_recipe_id")
    field = context.user_data.get("edit_field")

    session = get_session()
    try:
        recipe_service = RecipeService(session)
        recipe = recipe_service.get_by_id(recipe_id)

        if not recipe:
            await update.message.reply_text("Recipe not found.")
            return ConversationHandler.END

        if field == "edit_name":
            existing = recipe_service.get_by_name(value)
            if existing and existing.id != recipe_id:
                await update.message.reply_text(f"Recipe '{value}' already exists.")
                return ENTER_VALUE
            recipe.name = value
            session.commit()
            await update.message.reply_text(f"✅ Name updated to: {value}")

        elif field == "edit_category":
            if value.lower() not in CATEGORIES:
                await update.message.reply_text(
                    f"Invalid category. Valid: " + ", ".join(CATEGORIES)
                )
                return ENTER_VALUE
            recipe.category = value.lower()
            session.commit()
            await update.message.reply_text(f"✅ Category: {value}")

        elif field == "edit_needs_side":
            needs = value.lower() in ["yes", "sì", "s", "true", "1"]
            recipe.needs_side = needs
            session.commit()
            await update.message.reply_text(f"✅ Needs side: {'Yes' if needs else 'No'}")

        elif field == "edit_suggested_side":
            if value.lower() in ["none", "nessuno", "-"]:
                recipe.suggested_side = None
                session.commit()
                await update.message.reply_text("✅ Suggested side cleared.")
            else:
                recipe.suggested_side = value
                session.commit()
                await update.message.reply_text(f"✅ Suggested side: {value}")

        elif field == "edit_external":
            external_service = ExternalIngredientService(session)
            if value.lower() in ["none", "nessuno", "-"]:
                external_service.set_no_external(recipe_id)
                await update.message.reply_text("✅ Marked as no external ingredients.")
            else:
                ingredients = [ing.strip() for ing in value.split(",") if ing.strip()]
                external_service.set_ingredients(recipe_id, ingredients)
                ing_text = ", ".join(ingredients)
                await update.message.reply_text(f"✅ External ingredients: {ing_text}")

        return ConversationHandler.END

    finally:
        session.close()


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel editing."""
    await update.message.reply_text("Editing cancelled.")
    return ConversationHandler.END


def get_edit_handler():
    """Return ConversationHandler for /edit command."""
    return ConversationHandler(
        entry_points=[CommandHandler("edit", edit_start)],
        states={
            CHOOSE_FIELD: [CallbackQueryHandler(handle_field_choice)],
            ENTER_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_value_entry)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
