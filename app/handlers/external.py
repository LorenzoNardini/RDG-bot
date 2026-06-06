from telegram import Update
from telegram.ext import ContextTypes
from app.database.db import get_session
from app.services.external_service import ExternalIngredientService


async def external_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /external command.
    Batch mode: /external 1 jackfruit; 2 turmeric; 3 salt
    Single mode: /external 1 salmon fillet, dill
    """
    session = get_session()
    try:
        # Parse arguments
        if not context.args or len(context.args) < 2:
            await update.message.reply_text(
                "Usage (single): /external 1 salmon, dill\n"
                "Usage (batch): /external 1 jackfruit; 2 turmeric; 3 salt"
            )
            return

        # Get enrichment recipes mapping
        enrichment_recipes = context.user_data.get("enrichment_recipes", {})
        if not enrichment_recipes:
            await update.message.reply_text(
                "No enrichment session active. Run /fill_missing first."
            )
            return

        from app.services.recipe_service import RecipeService
        recipe_service = RecipeService(session)
        external_service = ExternalIngredientService(session)

        # Join all args
        raw_input = " ".join(context.args)

        # Check if batch mode (contains semicolons)
        if ";" in raw_input:
            # Batch mode: parse "1 jackfruit; 2 turmeric; 3 salt"
            batches = raw_input.split(";")
            saved = []
            failed = []

            for batch in batches:
                batch = batch.strip()
                if not batch:
                    continue

                parts = batch.split(None, 1)
                if len(parts) < 2:
                    failed.append(f"'{batch}' (missing position or ingredients)")
                    continue

                try:
                    position = int(parts[0])
                except ValueError:
                    failed.append(f"'{batch}' (invalid position)")
                    continue

                if position not in enrichment_recipes:
                    failed.append(f"Position {position} (not in enrichment)")
                    continue

                recipe_id = enrichment_recipes[position]
                recipe = recipe_service.get_by_id(recipe_id)
                if not recipe:
                    failed.append(f"Position {position} (recipe not found)")
                    continue

                # Parse ingredients
                ingredients_str = parts[1].strip()
                ingredients = [ing.strip() for ing in ingredients_str.split(",") if ing.strip()]

                if not ingredients:
                    failed.append(f"Position {position} (no ingredients)")
                    continue

                # Save
                external_service.set_ingredients(recipe_id, ingredients)
                ing_list = ", ".join(ingredients)
                saved.append(f"  ✅ {recipe.name}: {ing_list}")
                del enrichment_recipes[position]

            context.user_data["enrichment_recipes"] = enrichment_recipes

            # Show results
            msg = ""
            if saved:
                msg += "Saved:\n" + "\n".join(saved) + "\n"
            if failed:
                msg += "\nFailed:\n" + "\n".join(f"  ❌ {f}" for f in failed)

            await update.message.reply_text(msg if msg else "No changes made.")

            if not enrichment_recipes:
                await update.message.reply_text("✨ All external ingredient info is now complete!")
        else:
            # Single mode: "1 salmon, dill"
            parts = raw_input.split(None, 1)
            if len(parts) < 2:
                await update.message.reply_text("Usage: /external 1 salmon, dill")
                return

            try:
                position = int(parts[0])
            except ValueError:
                await update.message.reply_text(f"Invalid position: {parts[0]}")
                return

            if position not in enrichment_recipes:
                available = ", ".join(str(p) for p in sorted(enrichment_recipes.keys()))
                await update.message.reply_text(
                    f"Position {position} not in enrichment. Available: {available}"
                )
                return

            recipe_id = enrichment_recipes[position]
            recipe = recipe_service.get_by_id(recipe_id)
            if not recipe:
                await update.message.reply_text("Recipe not found.")
                return

            # Parse ingredients (stop at next slash command)
            ingredients_str = parts[1].strip()
            ingredients_tokens = []
            for token in ingredients_str.split():
                if token.startswith("/"):
                    break
                ingredients_tokens.append(token)
            ingredients_text = " ".join(ingredients_tokens)
            ingredients = [ing.strip() for ing in ingredients_text.split(",") if ing.strip()]

            if not ingredients:
                await update.message.reply_text("Please provide at least one ingredient.")
                return

            # Save
            external_service.set_ingredients(recipe_id, ingredients)
            ing_list = ", ".join(ingredients)
            await update.message.reply_text(f"✅ {recipe.name}\nExternal ingredients: {ing_list}")

            # Remove from enrichment
            del enrichment_recipes[position]
            context.user_data["enrichment_recipes"] = enrichment_recipes

            if not enrichment_recipes:
                await update.message.reply_text("✨ All external ingredient info is now complete!")
            elif context.user_data.get("enrichment_mode") == "conversational":
                # In conversational mode, ask for next recipe
                remaining_positions = sorted(enrichment_recipes.keys())
                if remaining_positions:
                    next_pos = remaining_positions[0]
                    next_recipe_id = enrichment_recipes[next_pos]
                    next_recipe = recipe_service.get_by_id(next_recipe_id)
                    if next_recipe:
                        prompt = (
                            f"📝 *Next one:*\n\n"
                            f"For: *{next_recipe.name}*\n\n"
                            f"Reply with:\n"
                            f"• `/external {next_pos} jackfruit, turmeric`\n"
                            f"• `/noexternal {next_pos}`\n"
                            f"• `/skip` to skip all"
                        )
                        await update.message.reply_text(prompt, parse_mode="Markdown")

    finally:
        session.close()


async def noexternal_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /noexternal command.
    Usage: /noexternal <number|numbers>
    Marks one or more recipes as having no external ingredients needed.
    Examples: /noexternal 2, /noexternal 1 2 4, /noexternal 1, 2, 4
    """
    session = get_session()
    try:
        # Parse positions
        if not context.args:
            await update.message.reply_text(
                "Usage: /noexternal <number> or /noexternal <numbers>\n"
                "Examples: /noexternal 2, /noexternal 1 2 4"
            )
            return

        # Join all args and parse comma/space separated values
        raw_arg = " ".join(context.args)
        positions_str = raw_arg.replace(",", " ")
        position_strs = positions_str.split()

        positions = []
        for pos_str in position_strs:
            try:
                pos = int(pos_str)
                positions.append(pos)
            except ValueError:
                await update.message.reply_text(
                    f"Invalid position: {pos_str}. Use numbers only."
                )
                return

        if not positions:
            await update.message.reply_text("No valid positions provided.")
            return

        # Get enrichment recipes mapping
        enrichment_recipes = context.user_data.get("enrichment_recipes", {})
        if not enrichment_recipes:
            await update.message.reply_text(
                "No enrichment session active. Run /fill_missing first."
            )
            return

        # Check all positions exist
        invalid = [p for p in positions if p not in enrichment_recipes]
        if invalid:
            available = ", ".join(str(p) for p in sorted(enrichment_recipes.keys()))
            await update.message.reply_text(
                f"Position(s) {', '.join(map(str, invalid))} not in current enrichment.\n"
                f"Available: {available}"
            )
            return

        # Mark each as no external ingredients
        from app.services.recipe_service import RecipeService
        recipe_service = RecipeService(session)
        external_service = ExternalIngredientService(session)

        marked = []
        for position in positions:
            recipe_id = enrichment_recipes[position]
            recipe = recipe_service.get_by_id(recipe_id)
            if recipe:
                external_service.set_no_external(recipe_id)
                marked.append(f"  ✅ {recipe.name}")
                del enrichment_recipes[position]

        context.user_data["enrichment_recipes"] = enrichment_recipes

        # Show confirmation
        if marked:
            msg = "Marked as having no external ingredients:\n" + "\n".join(marked)
            await update.message.reply_text(msg)

        # If no more to enrich, say so
        if not enrichment_recipes:
            await update.message.reply_text("✨ All external ingredient info is now complete!")
        elif context.user_data.get("enrichment_mode") == "conversational" and len(positions) == 1:
            # In conversational mode and only marked one recipe, ask for next
            remaining_positions = sorted(enrichment_recipes.keys())
            if remaining_positions:
                next_pos = remaining_positions[0]
                next_recipe_id = enrichment_recipes[next_pos]
                next_recipe = recipe_service.get_by_id(next_recipe_id)
                if next_recipe:
                    prompt = (
                        f"📝 *Next one:*\n\n"
                        f"For: *{next_recipe.name}*\n\n"
                        f"Reply with:\n"
                        f"• `/external {next_pos} jackfruit, turmeric`\n"
                        f"• `/noexternal {next_pos}`\n"
                        f"• `/skip` to skip all"
                    )
                    await update.message.reply_text(prompt, parse_mode="Markdown")

    finally:
        session.close()


async def skip_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /skip command.
    Dismisses the current enrichment session without blocking workflow.
    """
    context.user_data["enrichment_recipes"] = {}
    await update.message.reply_text(
        "Skipped enrichment. You can always use /fill_missing later to improve the database.",
        parse_mode="Markdown"
    )
