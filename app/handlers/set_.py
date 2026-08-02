from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters
from app.database.db import get_session
from app.services.menu_service import MenuService
from app.services.recipe_service import RecipeService
from app.utils.formatting import format_menu, format_recipe_selection, format_category_selection

CATEGORIES = ["carne rossa", "carne bianca", "pesce", "uova", "legumi", "altro"]


async def set_number_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle plain number input after /set command.
    Allows user to just type a number instead of /set <position> <number>.

    IMPORTANT: This handler only processes if in an active /set flow.
    It must be registered AFTER conversation handlers to avoid interfering with /add, /edit, etc.
    """
    # Check if there's a pending selection state (only active during /set flow)
    set_selection = context.user_data.get("set_selection", {})
    if not set_selection:
        # No pending selection, don't handle this message
        # (allow other handlers to process it)
        return

    pending_menu_id = context.user_data.get("pending_menu_id")
    if not pending_menu_id:
        # No pending menu, don't handle
        return

    # Parse the message as a number
    try:
        number = int(update.message.text.strip())
    except ValueError:
        # Not a pure number, ignore
        return

    session = get_session()
    try:

        position = set_selection.get("position")
        category_number = set_selection.get("category_number")

        # Route based on current state
        if position is None:
            # Should not happen, but safety check
            return

        if position == 7 and category_number is None:
            # User is at stage: /set 7 → just typed a number (category selection)
            await _show_recipes_for_category_7(session, update, context, pending_menu_id, str(number))
            return

        if position == 7 and category_number is not None:
            # User is at stage: /set 7 2 → just typed a number (recipe selection for position 7)
            await _set_recipe_for_position_7(
                session, update, context, pending_menu_id, str(category_number), str(number)
            )
            return

        if position >= 1 and position <= 6:
            # User is at stage: /set <position> → just typed a number (recipe selection for position 1-6)
            await _set_recipe_for_position(session, update, context, pending_menu_id, position, str(number))
            return

    finally:
        session.close()


def get_set_number_handler():
    """Return a MessageHandler for plain number input during /set flow.

    DEPRECATED: This handler is no longer registered globally to prevent
    interference with other conversation handlers (/add, /edit, etc).

    Users should use the full `/set position recipe_number` syntax instead.
    This handler is kept for reference only.
    """
    return MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        set_number_input
    )


async def set_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /set command for deterministic recipe replacement.

    Forms:
    1. /set <position> → Show recipe list for that position
    2. /set <position> <recipe_number> → Set the recipe
    3. /set 7 → Show category selection (position 7 has no fixed category)
    4. /set 7 <category_number> → Show recipes from that category
    5. /set 7 <category_number> <recipe_number> → Set the recipe
    """
    session = get_session()
    try:
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
                "• Show recipes: `/set 2`\n"
                "• Set recipe: `/set 2 3`\n"
                "• Position 7 (choose category first): `/set 7`",
                parse_mode="Markdown"
            )
            return

        # Parse position
        try:
            position = int(context.args[0])
            if position < 1 or position > 7:
                await update.message.reply_text("Position must be between 1 and 7.")
                return
        except ValueError:
            await update.message.reply_text("First argument must be a position number (1-7).")
            return

        # If only position provided
        if len(context.args) == 1:
            await _show_recipe_list(session, update, context, pending_menu_id, position)
            return

        # If position + recipe_number provided (and not position 7)
        if position != 7:
            if len(context.args) != 2:
                await update.message.reply_text(
                    f"Usage: `/set {position} <recipe_number>`",
                    parse_mode="Markdown"
                )
                return
            await _set_recipe_for_position(session, update, context, pending_menu_id, position, context.args[1])
            return

        # Position 7 cases
        if len(context.args) == 2:
            # /set 7 <category_number>
            await _show_recipes_for_category_7(session, update, context, pending_menu_id, context.args[1])
            return

        if len(context.args) == 3:
            # /set 7 <category_number> <recipe_number>
            await _set_recipe_for_position_7(
                session, update, context, pending_menu_id, context.args[1], context.args[2]
            )
            return

        # Too many arguments
        await update.message.reply_text(
            "Too many arguments. Use `/set <position> [recipe_number]`",
            parse_mode="Markdown"
        )

    finally:
        session.close()


async def _show_recipe_list(
    session, update: Update, context: ContextTypes.DEFAULT_TYPE, menu_id: int, position: int
):
    """
    Show recipe list for a given position.
    For positions 1-6: show recipes from current category.
    For position 7: show category selection.
    """
    menu_service = MenuService(session)
    items = menu_service.get_menu_items(menu_id)
    recipe_service = RecipeService(session)

    # Get current item at position
    current_item = next((i for i in items if i.position == position), None)
    if not current_item:
        await update.message.reply_text(f"Position {position} not found in menu.")
        return

    if position == 7:
        # Show category selection
        text = format_category_selection()
        await update.message.reply_text(text, parse_mode="Markdown")
        # Store state for next step
        context.user_data["set_selection"] = {"position": 7}
        return

    # Positions 1-6: get recipes from current category
    current_category = current_item.recipe.category
    recipes = recipe_service.get_by_category(current_category)

    if not recipes:
        await update.message.reply_text(f"No recipes found in category {current_category}.")
        return

    # Store choices in context for next command
    sorted_recipes = sorted(recipes, key=lambda r: r.name)
    choices = {i: r.id for i, r in enumerate(sorted_recipes, 1)}

    context.user_data["set_selection"] = {
        "position": position,
        "category": current_category,
        "choices": choices,
    }

    text = format_recipe_selection(sorted_recipes, position, current_category)
    await update.message.reply_text(text, parse_mode="Markdown")


async def _set_recipe_for_position(
    session, update: Update, context: ContextTypes.DEFAULT_TYPE, menu_id: int, position: int, recipe_number_str: str
):
    """Set a recipe for positions 1-6."""
    menu_service = MenuService(session)

    # Get stored selection state
    set_selection = context.user_data.get("set_selection", {})
    choices = set_selection.get("choices", {})

    if not choices or set_selection.get("position") != position:
        # State expired or invalid
        await update.message.reply_text(
            f"Selection expired. Run `/set {position}` again.",
            parse_mode="Markdown"
        )
        return

    # Parse recipe number
    try:
        recipe_number = int(recipe_number_str)
        if recipe_number not in choices:
            await update.message.reply_text(
                f"Invalid recipe number. Choose between 1 and {len(choices)}."
            )
            return
    except ValueError:
        await update.message.reply_text("Recipe number must be an integer.")
        return

    recipe_id = choices[recipe_number]

    # Use service to replace recipe
    result = menu_service.replace_position_with_recipe(menu_id, position, recipe_id)

    if not result["success"]:
        await update.message.reply_text(f"❌ {result['error']}")
        return

    # Show updated menu
    menu = menu_service.get_menu(menu_id)
    items = menu_service.get_menu_items(menu_id)
    menu_text = format_menu(menu, items)
    menu_text += f"\n\n✅ Position {position} updated!"

    await update.message.reply_text(menu_text, parse_mode="Markdown")

    # Clear selection state
    context.user_data.pop("set_selection", None)


async def _show_recipes_for_category_7(
    session, update: Update, context: ContextTypes.DEFAULT_TYPE, menu_id: int, category_number_str: str
):
    """Show recipes for position 7 after category selection."""
    recipe_service = RecipeService(session)

    # Parse category number
    try:
        category_number = int(category_number_str)
        if category_number < 1 or category_number > 6:
            await update.message.reply_text("Category number must be between 1 and 6.")
            return
    except ValueError:
        await update.message.reply_text("Category number must be an integer.")
        return

    category = CATEGORIES[category_number - 1]
    recipes = recipe_service.get_by_category(category)

    if not recipes:
        await update.message.reply_text(f"No recipes found in category {category}.")
        return

    # Store choices in context
    sorted_recipes = sorted(recipes, key=lambda r: r.name)
    choices = {i: r.id for i, r in enumerate(sorted_recipes, 1)}

    context.user_data["set_selection"] = {
        "position": 7,
        "category": category,
        "category_number": category_number,
        "choices": choices,
    }

    text = format_recipe_selection(sorted_recipes, 7, category)
    await update.message.reply_text(text, parse_mode="Markdown")


async def _set_recipe_for_position_7(
    session, update: Update, context: ContextTypes.DEFAULT_TYPE, menu_id: int,
    category_number_str: str, recipe_number_str: str
):
    """Set a recipe for position 7 (final step)."""
    menu_service = MenuService(session)

    # Get stored selection state
    set_selection = context.user_data.get("set_selection", {})
    choices = set_selection.get("choices", {})

    if not choices or set_selection.get("position") != 7:
        # State expired or invalid
        await update.message.reply_text(
            "Selection expired. Run `/set 7` again.",
            parse_mode="Markdown"
        )
        return

    # Verify category number matches stored state
    try:
        provided_category_number = int(category_number_str)
        stored_category_number = set_selection.get("category_number")
        if provided_category_number != stored_category_number:
            await update.message.reply_text(
                "Category number mismatch. Run `/set 7` again.",
                parse_mode="Markdown"
            )
            return
    except ValueError:
        await update.message.reply_text("Category number must be an integer.")
        return

    # Parse recipe number
    try:
        recipe_number = int(recipe_number_str)
        if recipe_number not in choices:
            await update.message.reply_text(
                f"Invalid recipe number. Choose between 1 and {len(choices)}."
            )
            return
    except ValueError:
        await update.message.reply_text("Recipe number must be an integer.")
        return

    recipe_id = choices[recipe_number]

    # Use service to replace recipe
    result = menu_service.replace_position_with_recipe(menu_id, 7, recipe_id)

    if not result["success"]:
        await update.message.reply_text(f"❌ {result['error']}")
        return

    # Show updated menu
    menu = menu_service.get_menu(menu_id)
    items = menu_service.get_menu_items(menu_id)
    menu_text = format_menu(menu, items)
    menu_text += f"\n\n✅ Position 7 updated!"

    await update.message.reply_text(menu_text, parse_mode="Markdown")

    # Clear selection state
    context.user_data.pop("set_selection", None)
