from telegram import Update
from telegram.ext import ContextTypes
from app.database.db import get_session
from app.models.models import Recipe, ExternalIngredient

async def diagnose_external(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Diagnostic command to show which recipes need re-enrichment.
    Compares external_ingredients table with recipes.external_status.
    """
    session = get_session()
    try:
        # Find all recipes with external_ingredient records
        recipes_with_data = session.query(Recipe).join(ExternalIngredient).distinct().all()

        if not recipes_with_data:
            await update.message.reply_text("No external ingredients found in database.")
            return

        # Organize by status
        mismatched = []
        synced = []

        for recipe in recipes_with_data:
            ingredients = session.query(ExternalIngredient).filter(
                ExternalIngredient.recipe_id == recipe.id
            ).all()
            ing_names = [ing.ingredient_name for ing in ingredients]

            if recipe.external_status != "defined":
                mismatched.append({
                    "name": recipe.name,
                    "id": recipe.id,
                    "status": recipe.external_status,
                    "ingredients": ing_names
                })
            else:
                synced.append({
                    "name": recipe.name,
                    "id": recipe.id,
                    "ingredients": ing_names
                })

        # Build report
        msg = "[DIAGNOSTIC REPORT]\n\n"

        if synced:
            msg += f"[OK] {len(synced)} recipes are synced:\n"
            for r in synced[:10]:  # Show first 10
                msg += f"  • {r['name']}\n"
            if len(synced) > 10:
                msg += f"  ... and {len(synced) - 10} more\n"

        msg += "\n"

        if mismatched:
            msg += f"[ACTION NEEDED] {len(mismatched)} recipes need sync:\n\n"
            for r in mismatched:
                msg += f"Recipe: {r['name']} (ID: {r['id']})\n"
                msg += f"  Current status: '{r['status']}'\n"
                msg += f"  Has ingredients: {', '.join(r['ingredients'][:3])}"
                if len(r['ingredients']) > 3:
                    msg += f", ..."
                msg += "\n"
                msg += f"  Ingredients: {', '.join(r['ingredients'])}\n\n"

            msg += "\nTO FIX:\n"
            msg += "1. Run /fill_missing\n"
            msg += "2. You'll see these recipes again in enrichment\n"
            msg += "3. Reply with /external to set ingredients\n"
            msg += "   (or /noexternal if no external needed)\n"
        else:
            msg += "[OK] All recipes are properly synced!"

        await update.message.reply_text(msg)

    finally:
        session.close()
