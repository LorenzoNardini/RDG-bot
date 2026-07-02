from telegram import Update
from telegram.ext import ContextTypes
from app.database.db import get_session
from app.services.menu_service import MenuService
from app.utils.formatting import format_menu


async def roll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /roll command - generate a new weekly menu."""
    session = get_session()
    try:
        menu_service = MenuService(session)
        menu = menu_service.generate_week()

        if not menu:
            await update.message.reply_text(
                "❌ Cannot generate menu. Check that all categories have recipes.",
                parse_mode="Markdown"
            )
            return

        # Store pending menu ID in context (per user)
        user_id = update.effective_user.id
        context.user_data["pending_menu_id"] = menu.id

        # Get menu items and format
        items = menu_service.get_menu_items(menu.id)
        menu_text = format_menu(menu, items)

        # Add hints for menu modification
        menu_text += "\n_Sorprendimi (randomico):_\n"
        menu_text += "• /reroll pesce (categoria)\n"
        menu_text += "• /reroll 3 (posizione singola)\n"
        menu_text += "• /reroll 1 2 4 (posizioni multiple)\n"
        menu_text += "\n_Scegli tu (deterministico):_\n"
        menu_text += "• /set 2 (scegli da posizione 2)\n"
        menu_text += "• /set 7 (scegli da categoria per pos 7)\n"
        menu_text += "\n_Finalizza:_\n"
        menu_text += "• /accept quando sei soddisfatto"

        await update.message.reply_text(menu_text, parse_mode="Markdown")

    finally:
        session.close()
