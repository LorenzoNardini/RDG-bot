from telegram import Update
from telegram.ext import ContextTypes
from app.database.db import get_session
from app.services.menu_service import MenuService
from app.services.external_service import ExternalIngredientService
from app.services.shopping_service import ShoppingReminderService
from app.utils.formatting import format_menu


async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /history command - show recent accepted menus."""
    session = get_session()
    try:
        menu_service = MenuService(session)
        menus = menu_service.get_recent_accepted_menus(limit=5)

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

                # Add external ingredients for this menu (only those with defined ingredients)
                external_items = []
                for item in items:
                    # Ensure recipe is loaded in current session
                    if item.recipe is None:
                        continue
                    recipe = item.recipe
                    status = external_service.get_status(recipe.id)
                    if status == "defined":
                        ingredients = external_service.get_ingredients(recipe.id)
                        ing_text = ", ".join(ingredients)
                        external_items.append(f"  • {recipe.name}: {ing_text}")

                if external_items:
                    text += "\n*🛒 Ingredienti Esterni:*\n"
                    text += "\n".join(external_items) + "\n"

                text += "\n---\n\n"

            # Add current shopping reminders
            reminders = shopping_service.get_active_reminders()
            if reminders:
                text += "\n*📝 Promemoria Attuali:*\n"
                for item in reminders:
                    text += f"  • {item}\n"
                text += "\nPuoi aggiungere altri articoli con `/remember`\n"
            else:
                text += "\n_Nessun promemoria attivo. Usa `/remember` per aggiungere articoli da comprare._\n"

            await update.message.reply_text(text)

        except Exception as e:
            await update.message.reply_text(
                f"Error loading history: {str(e)}\n\nPlease try again."
            )

    finally:
        session.close()
