from telegram import Update
from telegram.ext import ContextTypes
from app.database.db import get_session
from app.services.menu_service import MenuService
from app.utils.formatting import format_menu

CATEGORIES = ["carne rossa", "carne bianca", "pesce", "uova", "legumi", "altro"]


async def reroll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /reroll command.
    Usage: /reroll <category> or /reroll <position>
    Examples: /reroll pesce, /reroll 3
    """
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

        if not menu or menu.is_accepted():
            await update.message.reply_text(
                "❌ Invalid menu. Run /roll first.",
                parse_mode="Markdown"
            )
            return

        # Parse argument
        if not context.args:
            await update.message.reply_text(
                "Usage: /reroll <category|position>\n"
                "Examples: /reroll pesce, /reroll 3",
                parse_mode="Markdown"
            )
            return

        arg = context.args[0].lower()

        # Check if it's a category or position
        if arg in CATEGORIES:
            # Reroll by category
            success = menu_service.reroll_category(pending_menu_id, arg)
            if not success:
                await update.message.reply_text(f"❌ Cannot reroll category: {arg}")
                return
            feedback = f"♻️ {arg.title()} regenerated!"
        else:
            # Try to parse as position
            try:
                position = int(arg)
                if position < 1 or position > 7:
                    await update.message.reply_text("❌ Position must be between 1 and 7.")
                    return
                success = menu_service.reroll_position(pending_menu_id, position)
                if not success:
                    await update.message.reply_text(f"❌ Cannot reroll position {position}.")
                    return
                feedback = f"♻️ Position {position} regenerated!"
            except ValueError:
                await update.message.reply_text(
                    f"❌ Invalid argument: {arg}\n"
                    "Use category name or position (1-7).",
                    parse_mode="Markdown"
                )
                return

        # Show updated menu
        items = menu_service.get_menu_items(pending_menu_id)
        menu_text = format_menu(menu, items)
        menu_text += f"\n\n{feedback}"

        await update.message.reply_text(menu_text, parse_mode="Markdown")

    finally:
        session.close()
