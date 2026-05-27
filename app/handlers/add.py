from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
from app.database.db import get_session
from app.services.recipe_service import RecipeService

# Conversation states
ADD_NAME, ADD_CATEGORY, ADD_NEEDS_SIDE, ADD_SIDE = range(4)

CATEGORIES = ["carne rossa", "carne bianca", "pesce", "uova", "legumi", "altro"]
SIDE_CHOICES = ["Sì", "No"]


async def add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the /add conversation."""
    await update.message.reply_text(
        "Aggiungiamo una nuova ricetta! 📝\n\nQuale è il nome della ricetta?",
        reply_markup=ReplyKeyboardRemove()
    )
    return ADD_NAME


async def add_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get recipe name."""
    context.user_data["recipe_name"] = update.message.text

    keyboard = [[cat.title()] for cat in CATEGORIES]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, input_field_placeholder="Seleziona categoria...")

    await update.message.reply_text(
        "Seleziona la categoria:",
        reply_markup=reply_markup
    )
    return ADD_CATEGORY


async def add_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get recipe category."""
    category = update.message.text.lower()
    if category not in CATEGORIES:
        await update.message.reply_text(f"❌ Categoria non valida. Prova di nuovo.")
        return ADD_CATEGORY

    context.user_data["recipe_category"] = category

    keyboard = [[choice] for choice in SIDE_CHOICES]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)

    await update.message.reply_text(
        "Questa ricetta ha bisogno di un contorno?",
        reply_markup=reply_markup
    )
    return ADD_NEEDS_SIDE


async def add_needs_side(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get if recipe needs side."""
    needs_side = update.message.text.lower() == "sì"
    context.user_data["recipe_needs_side"] = needs_side

    if needs_side:
        await update.message.reply_text(
            "Quale contorno suggerisci?",
            reply_markup=ReplyKeyboardRemove()
        )
        return ADD_SIDE
    else:
        # Skip side, save recipe
        session = get_session()
        try:
            recipe_service = RecipeService(session)
            recipe = recipe_service.create(
                name=context.user_data["recipe_name"],
                category=context.user_data["recipe_category"],
                needs_side=False
            )
            await update.message.reply_text(
                f"✅ Ricetta aggiunta: *{recipe.name}*",
                parse_mode="Markdown"
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Errore: {str(e)}")
        finally:
            session.close()

        context.user_data.clear()
        return ConversationHandler.END


async def add_side(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get suggested side and save recipe."""
    session = get_session()
    try:
        recipe_service = RecipeService(session)
        recipe = recipe_service.create(
            name=context.user_data["recipe_name"],
            category=context.user_data["recipe_category"],
            needs_side=context.user_data["recipe_needs_side"],
            suggested_side=update.message.text
        )
        await update.message.reply_text(
            f"✅ Ricetta aggiunta: *{recipe.name}* (+ {recipe.suggested_side})",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Errore: {str(e)}")
    finally:
        session.close()

    context.user_data.clear()
    return ConversationHandler.END


async def add_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the /add conversation."""
    await update.message.reply_text(
        "Annullato! ❌",
        reply_markup=ReplyKeyboardRemove()
    )
    context.user_data.clear()
    return ConversationHandler.END


def get_add_handler():
    """Return the ConversationHandler for /add."""
    from telegram.ext import CommandHandler, MessageHandler, filters

    return ConversationHandler(
        entry_points=[CommandHandler("add", add_start)],
        states={
            ADD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_name)],
            ADD_CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_category)],
            ADD_NEEDS_SIDE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_needs_side)],
            ADD_SIDE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_side)],
        },
        fallbacks=[CommandHandler("cancel", add_cancel)],
        allow_reentry=True
    )
