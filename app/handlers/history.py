from telegram import Update
from telegram.ext import ContextTypes
from app.database.db import get_session
from app.services.menu_service import MenuService
from app.services.external_service import ExternalIngredientService
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

        await update.message.reply_text(text, parse_mode="Markdown")

    finally:
        session.close()
