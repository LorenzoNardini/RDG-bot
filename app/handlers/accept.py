from telegram import Update
from telegram.ext import ContextTypes
from app.database.db import get_session
from app.services.menu_service import MenuService
from app.utils.formatting import format_menu


async def accept(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /accept command - save pending menu to history."""
    session = get_session()
    try:
        user_id = update.effective_user.id
        pending_menu_id = context.user_data.get("pending_menu_id")

        if not pending_menu_id:
            await update.message.reply_text(
                "❌ No pending menu. Run /roll first.",
                parse_mode="Markdown"
            )
            return

        menu_service = MenuService(session)
        menu = menu_service.get_menu(pending_menu_id)

        if not menu:
            await update.message.reply_text(
                "❌ Invalid menu.",
                parse_mode="Markdown"
            )
            return

        if menu.is_accepted():
            await update.message.reply_text(
                "✅ This menu is already accepted.",
                parse_mode="Markdown"
            )
            return

        # Accept the menu
        menu_service.accept_menu(pending_menu_id)

        # Clear pending menu from context
        context.user_data["pending_menu_id"] = None

        # Show confirmation
        items = menu_service.get_menu_items(pending_menu_id)
        menu_text = format_menu(menu, items)
        menu_text += "\n\n✅ *Menu accettato e salvato in storia!*"

        await update.message.reply_text(menu_text, parse_mode="Markdown")

    finally:
        session.close()
