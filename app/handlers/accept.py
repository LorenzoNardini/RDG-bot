from telegram import Update
from telegram.ext import ContextTypes
from app.database.db import get_session
from app.services.menu_service import MenuService
from app.services.external_service import ExternalIngredientService
from app.services.shopping_service import ShoppingReminderService
from app.utils.formatting import format_menu, format_enrichment_prompt, format_shopping_summary


async def accept(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /accept command - save pending menu to history."""
    # Clear any stale enrichment state from previous /accept calls
    context.user_data["enrichment_recipes"] = {}
    context.user_data["enrichment_mode"] = None
    context.user_data["enrichment_index"] = None

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

        # Collect external ingredients for recipes that have them defined
        recipe_ids = [item.recipe_id for item in items]
        external_service = ExternalIngredientService(session)
        external_items = []
        for recipe_id in recipe_ids:
            if external_service.get_status(recipe_id) == "defined":
                ingredients = external_service.get_ingredients(recipe_id)
                external_items.extend(ingredients)

        # Get shopping reminders
        shopping_service = ShoppingReminderService(session)
        reminders = shopping_service.get_active_reminders()

        # Show combined shopping summary if there are items
        if external_items or reminders:
            summary = format_shopping_summary(external_items, reminders)
            await update.message.reply_text(summary, parse_mode="Markdown")
            # Clear reminders after displaying them
            shopping_service.clear_reminders()

        # Check for recipes needing external ingredient enrichment
        unknown_recipes = external_service.get_recipes_needing_enrichment(recipe_ids)

        if unknown_recipes:
            # Build numbered mapping and start conversational mode
            enrichment_recipes = {i: recipe.id for i, recipe in enumerate(unknown_recipes, 1)}
            context.user_data["enrichment_recipes"] = enrichment_recipes
            context.user_data["enrichment_mode"] = "conversational"
            context.user_data["enrichment_index"] = 0

            # Ask for first recipe conversationally
            first_recipe = unknown_recipes[0]
            prompt = (
                f"📝 *External ingredients needed?*\n\n"
                f"For: *{first_recipe.name}*\n\n"
                f"Reply with:\n"
                f"• `/external 1 jackfruit, turmeric`\n"
                f"• `/noexternal 1`\n"
                f"• `/skip` to skip all"
            )
            await update.message.reply_text(prompt, parse_mode="Markdown")

    finally:
        session.close()
