from telegram import Update
from telegram.ext import ContextTypes
from app.database.db import get_session
from app.services.menu_service import MenuService
from app.services.external_service import ExternalIngredientService
from app.services.shopping_service import ShoppingReminderService
from app.utils.formatting import format_menu


async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /history command - show recent accepted menus.
    Usage: /history (last 1 menu) or /history <n> (last n menus)
    """
    session = get_session()
    try:
        # Parse optional argument
        limit = 1
        if context.args:
            try:
                limit = int(context.args[0])
                if limit < 1:
                    await update.message.reply_text("Please provide a positive number.")
                    return
                # Cap at 10 to avoid excessive output
                limit = min(limit, 10)
            except ValueError:
                await update.message.reply_text("Please provide a valid number.")
                return

        menu_service = MenuService(session)
        menus = menu_service.get_recent_accepted_menus(limit=limit)

        if not menus:
            await update.message.reply_text(
                "📚 No saved menus yet. Run /roll and /accept to save one!",
                parse_mode="Markdown"
            )
            return

        text = "📚 *Ultimi Menu Accettati*\n\n"
        external_service = ExternalIngredientService(session)
        shopping_service = ShoppingReminderService(session)

        try:
            for i, menu in enumerate(menus, 1):
                accepted_date = menu.accepted_at.strftime("%d/%m/%Y %H:%M") if menu.accepted_at else "pending"
                text += f"*Menu #{i}* ({accepted_date})\n"

                items = menu_service.get_menu_items(menu.id)
                menu_text = format_menu(menu, items)

                # Remove title from menu_text
                menu_text = menu_text.split("\n", 1)[1] if "\n" in menu_text else menu_text

                text += menu_text

                # Add shopping list for this menu (external ingredients + reminders from current menu)
                external_items = []
                for item in items:
                    # Ensure recipe is loaded in current session
                    if item.recipe is None:
                        continue
                    recipe = item.recipe
                    status = external_service.get_status(recipe.id)
                    if status == "defined":
                        ingredients = external_service.get_ingredients(recipe.id)
                        for ing in ingredients:
                            external_items.append(ing)

                text += "\n---\n\n"

            # Add unified shopping list (external ingredients from all menus + current reminders)
            # Only show reminders once, after all menus
            all_external_items = []
            for menu in menus:
                items = menu_service.get_menu_items(menu.id)
                for item in items:
                    if item.recipe is None:
                        continue
                    recipe = item.recipe
                    status = external_service.get_status(recipe.id)
                    if status == "defined":
                        ingredients = external_service.get_ingredients(recipe.id)
                        all_external_items.extend(ingredients)

            reminders = shopping_service.get_active_reminders()
            all_shopping_items = all_external_items + reminders

            # Show unified shopping list
            if all_shopping_items:
                text += "*🛒 Lista della Spesa:*\n"
                for item in all_shopping_items:
                    text += f"  • {item}\n"
                text += "\nPuoi aggiungere altri articoli con `/remember` o segnare come comprati con `/bought`\n"
            else:
                text += "_Lista della spesa vuota. Usa `/remember` per aggiungere articoli da comprare._\n"

            await update.message.reply_text(text)

        except Exception as e:
            await update.message.reply_text(
                f"Error loading history: {str(e)}\n\nPlease try again."
            )

    finally:
        session.close()
