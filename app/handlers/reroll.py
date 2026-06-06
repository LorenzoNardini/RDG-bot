from telegram import Update
from telegram.ext import ContextTypes
from app.database.db import get_session
from app.services.menu_service import MenuService
from app.utils.formatting import format_menu

CATEGORIES = ["carne rossa", "carne bianca", "pesce", "uova", "legumi", "altro"]


async def reroll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /reroll command.
    Usage: /reroll <category>, /reroll <position>, or /reroll <positions>
    Examples: /reroll pesce, /reroll 3, /reroll 1 2 4, /reroll 1, 2, 4
    """
    session = get_session()
    try:
        user_id = update.effective_user.id
        pending_menu_id = context.user_data.get("pending_menu_id")

        if not pending_menu_id:
            await update.message.reply_text(
                "No pending menu. Run /roll first.",
                parse_mode="Markdown"
            )
            return

        menu_service = MenuService(session)
        menu = menu_service.get_menu(pending_menu_id)

        if not menu or menu.is_accepted():
            await update.message.reply_text(
                "Invalid menu. Run /roll first.",
                parse_mode="Markdown"
            )
            return

        # Parse arguments
        if not context.args:
            await update.message.reply_text(
                "Usage:\n"
                "• Category: `/reroll pesce`\n"
                "• Single position: `/reroll 3`\n"
                "• Multiple: `/reroll 1 2 4` or `/reroll 1, 2, 4`",
                parse_mode="Markdown"
            )
            return

        # Join all args and parse comma/space separated values
        raw_arg = " ".join(context.args).lower()

        # Check if it's a single category
        if raw_arg in CATEGORIES:
            success = menu_service.reroll_category(pending_menu_id, raw_arg)
            if not success:
                await update.message.reply_text(f"Cannot reroll category: {raw_arg}")
                return
            feedback = f"♻️ {raw_arg.title()} regenerated!"
        else:
            # Parse as positions (comma or space separated)
            positions_str = raw_arg.replace(",", " ")
            position_strs = positions_str.split()

            positions = []
            for pos_str in position_strs:
                try:
                    pos = int(pos_str)
                    if pos < 1 or pos > 7:
                        await update.message.reply_text(f"Position must be between 1 and 7, got {pos}.")
                        return
                    positions.append(pos)
                except ValueError:
                    await update.message.reply_text(
                        f"Invalid argument: {pos_str}\n"
                        "Use category name or position numbers (1-7).",
                        parse_mode="Markdown"
                    )
                    return

            if not positions:
                await update.message.reply_text("No valid positions provided.")
                return

            # Reroll each position
            failed = []
            for pos in positions:
                success = menu_service.reroll_position(pending_menu_id, pos)
                if not success:
                    failed.append(pos)

            if failed:
                await update.message.reply_text(f"Failed to reroll positions: {', '.join(map(str, failed))}")
                return

            if len(positions) == 1:
                feedback = f"♻️ Position {positions[0]} regenerated!"
            else:
                feedback = f"♻️ Positions {', '.join(map(str, positions))} regenerated!"

        # Show updated menu
        items = menu_service.get_menu_items(pending_menu_id)
        menu_text = format_menu(menu, items)
        menu_text += f"\n\n{feedback}"

        await update.message.reply_text(menu_text, parse_mode="Markdown")

    finally:
        session.close()
