from app.models.models import WeeklyMenu, WeeklyMenuItem, Recipe

CATEGORY_EMOJI = {
    "carne rossa": "🥩",
    "carne bianca": "🍗",
    "pesce": "🐟",
    "uova": "🥚",
    "legumi": "🫘",
    "altro": "🍝",
}


def format_menu(menu: WeeklyMenu, items: list[WeeklyMenuItem]) -> str:
    """
    Format a weekly menu for Telegram.
    Groups by category, shows numbered positions and sides.
    """
    if not items:
        return "Menu is empty."

    # Group items by category
    by_category = {}
    for item in items:
        cat = item.recipe.category
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(item)

    lines = ["🍽️ *Menu Settimanale*\n"]

    # Define category order
    category_order = ["carne rossa", "carne bianca", "pesce", "uova", "legumi", "altro"]

    for category in category_order:
        if category not in by_category:
            continue

        emoji = CATEGORY_EMOJI.get(category, "📌")
        lines.append(f"{emoji} _{category.title()}_")

        for item in sorted(by_category[category], key=lambda x: x.position):
            recipe = item.recipe
            side_note = ""
            if recipe.needs_side and recipe.suggested_side:
                side_note = f" (+ {recipe.suggested_side})"
            lines.append(f"  {item.position}. {recipe.name}{side_note}")

        lines.append("")

    return "\n".join(lines)


def format_recipe_list(recipes: list[Recipe]) -> str:
    """Format a list of recipes for Telegram."""
    if not recipes:
        return "No recipes found."

    lines = [f"📚 *Ricette* ({len(recipes)}):\n"]

    # Group by category
    by_category = {}
    for recipe in recipes:
        if recipe.category not in by_category:
            by_category[recipe.category] = []
        by_category[recipe.category].append(recipe)

    category_order = ["carne rossa", "carne bianca", "pesce", "uova", "legumi", "altro"]

    for category in category_order:
        if category not in by_category:
            continue

        emoji = CATEGORY_EMOJI.get(category, "📌")
        lines.append(f"{emoji} _{category.title()}_")

        for recipe in sorted(by_category[category], key=lambda x: x.name):
            side_note = ""
            if recipe.needs_side and recipe.suggested_side:
                side_note = f" (+ {recipe.suggested_side})"
            lines.append(f"  • {recipe.name}{side_note}")

        lines.append("")

    return "\n".join(lines)


def format_recipe(recipe: Recipe) -> str:
    """Format a single recipe for display."""
    text = f"*{recipe.name}*\n"
    text += f"Categoria: {recipe.category}\n"
    if recipe.needs_side:
        text += f"Contorno: {recipe.suggested_side or 'a scelta'}\n"
    return text


def format_enrichment_prompt(recipes: list[Recipe]) -> str:
    """Format enrichment prompt showing recipes that need external ingredient info."""
    if not recipes:
        return "No recipes need enrichment."

    lines = ["🛒 *External ingredient information missing*\n"]
    lines.append("I still don't know whether these recipes require ingredients purchased outside the online supermarket:\n")

    for i, recipe in enumerate(recipes, 1):
        lines.append(f"{i}. {recipe.name}")

    lines.append("")
    lines.append("Reply with:")
    lines.append("• `/external 1 salmon fillet, dill`")
    lines.append("• `/noexternal 2`")
    lines.append("• `/skip`")

    return "\n".join(lines)
