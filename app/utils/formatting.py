from app.models.models import WeeklyMenu, WeeklyMenuItem, Recipe


def format_consolidated_shopping_list(items: list[str]) -> str:
    """Format a unified shopping list (external ingredients + reminders combined)."""
    if not items:
        return "*🛒 Lista della Spesa:*\n_(vuota)_\n\nUsa `/remember` per aggiungere articoli da comprare."

    lines = ["*🛒 Lista della Spesa:*"]
    for item in sorted(set(items)):  # Deduplicate and sort
        lines.append(f"  • {item}")
    lines.append("\nUsa `/remember` per aggiungere altri articoli.")

    return "\n".join(lines)

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


def format_recipe_list(recipes: list[Recipe], show_external: bool = False) -> str:
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

            if show_external:
                if recipe.external_status == "defined" and recipe.external_ingredients:
                    ing_list = ", ".join([ing.ingredient_name for ing in recipe.external_ingredients])
                    lines.append(f"    🛒 {ing_list}")
                elif recipe.external_status == "none":
                    lines.append(f"    ✅ No external ingredients needed")

        lines.append("")

    return "\n".join(lines)


def format_recipe(recipe: Recipe) -> str:
    """Format a single recipe for display."""
    text = f"*{recipe.name}*\n"
    text += f"Categoria: {recipe.category}\n"
    if recipe.needs_side:
        text += f"Contorno: {recipe.suggested_side or 'a scelta'}\n"
    return text


def format_shopping_summary(external_ingredients: list[str], reminders: list[str]) -> str:
    """Format a consolidated shopping summary with both recipe ingredients and reminders."""
    if not external_ingredients and not reminders:
        return ""

    lines = ["\n🛒 *Things to buy outside the online supermarket*\n"]

    if external_ingredients:
        lines.append("*From recipes:*")
        for ing in external_ingredients:
            lines.append(f"  • {ing}")

    if reminders:
        if external_ingredients:
            lines.append("")
        lines.append("*General reminders:*")
        for item in reminders:
            lines.append(f"  • {item}")

    return "\n".join(lines)


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
    lines.append("• Single: `/external 1 salmon fillet, dill`")
    lines.append("• Batch: `/external 1 jackfruit; 2 turmeric; 3 salt`")
    lines.append("• No external: `/noexternal 1 2`")
    lines.append("• Skip: `/skip`")

    return "\n".join(lines)


def format_recipe_selection(recipes: list[Recipe], position: int, category: str = None) -> str:
    """Format a numbered list of recipes for /set selection."""
    if not recipes:
        return "No recipes found."

    emoji = CATEGORY_EMOJI.get(category, "📌") if category else "📌"
    header = f"{emoji} Position {position} ({category.title()})" if category else f"Position {position}"

    lines = [header, "", "Choose one recipe:"]

    # Sort alphabetically
    sorted_recipes = sorted(recipes, key=lambda r: r.name)
    for i, recipe in enumerate(sorted_recipes, 1):
        side_note = ""
        if recipe.needs_side and recipe.suggested_side:
            side_note = f" (+ {recipe.suggested_side})"
        lines.append(f"{i}. {recipe.name}{side_note}")

    lines.append("")
    lines.append(f"Reply with: `/set {position} <recipe_number>`")

    return "\n".join(lines)


def format_category_selection() -> str:
    """Format category selection for /set 7."""
    lines = [
        "Position 7 is a free choice.",
        "",
        "Choose a category:",
        "",
        "1. 🥩 Carne rossa",
        "2. 🍗 Carne bianca",
        "3. 🐟 Pesce",
        "4. 🥚 Uova",
        "5. 🫘 Legumi",
        "6. 🍝 Altro",
        "",
        "Reply with: `/set 7 <category_number>`",
    ]
    return "\n".join(lines)
