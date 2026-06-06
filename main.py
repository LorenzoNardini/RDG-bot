import logging
from pathlib import Path
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
)
from config import BOT_TOKEN
from app.database.db import init_db, get_session
from app.handlers.start import start, help_command
from app.handlers.roll import roll
from app.handlers.reroll import reroll
from app.handlers.accept import accept
from app.handlers.list_ import list_recipes
from app.handlers.history import history
from app.handlers.add import get_add_handler
from app.handlers.external import external_cmd, noexternal_cmd, skip_cmd
from app.handlers.fill_missing import fill_missing
from app.handlers.ingredients import ingredients_cmd
from app.handlers.edit import edit_start, get_edit_handler

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def _seed_recipes_from_excel(excel_path: str, recipe_service):
    """Seed recipes from Excel file."""
    import openpyxl
    try:
        wb = openpyxl.load_workbook(excel_path)
        ws = wb["Ricette"]

        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row[0]:
                continue

            name = row[0].strip() if row[0] else None
            category = row[1].strip().lower() if row[1] else None
            needs_side_text = row[2] if row[2] else "No"
            side = row[7].strip() if len(row) > 7 and row[7] else None

            if not name or not category:
                continue

            needs_side = needs_side_text.lower() in ["sì", "yes", "s", "true"]

            if not recipe_service.get_by_name(name):
                recipe_service.create(
                    name=name,
                    category=category,
                    needs_side=needs_side,
                    suggested_side=side
                )
    except Exception as e:
        logger.error(f"Error seeding recipes: {e}")


def main():
    """Run the bot."""
    # Initialize database
    init_db()
    logger.info("Database initialized.")

    # Auto-seed database on first startup if empty
    from app.services.recipe_service import RecipeService
    session = get_session()
    try:
        recipe_service = RecipeService(session)
        recipe_count = recipe_service.count_all()
        if recipe_count == 0:
            logger.info("Database is empty. Running seed script...")
            from pathlib import Path
            import openpyxl
            excel_path = Path(__file__).parent / "RDG.xlsx"
            if excel_path.exists():
                _seed_recipes_from_excel(str(excel_path), recipe_service)
                logger.info("Database seeded successfully.")
            else:
                logger.warning("RDG.xlsx not found. Skipping auto-seed.")
        else:
            logger.info(f"Database already has {recipe_count} recipes.")
    finally:
        session.close()

    # Create the Application
    app = Application.builder().token(BOT_TOKEN).build()

    # Register command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("roll", roll))
    app.add_handler(CommandHandler("reroll", reroll))
    app.add_handler(CommandHandler("accept", accept))
    app.add_handler(CommandHandler("list", list_recipes))
    app.add_handler(CommandHandler("history", history))
    app.add_handler(CommandHandler("external", external_cmd))
    app.add_handler(CommandHandler("noexternal", noexternal_cmd))
    app.add_handler(CommandHandler("skip", skip_cmd))
    app.add_handler(CommandHandler("fill_missing", fill_missing))
    app.add_handler(CommandHandler("ingredients", ingredients_cmd))
    app.add_handler(CommandHandler("edit", edit_start))

    # Register conversation handlers
    app.add_handler(get_add_handler())
    app.add_handler(get_edit_handler())

    # Start the bot
    logger.info("Starting bot...")
    app.run_polling(allowed_updates=["message", "edited_message"])


if __name__ == "__main__":
    main()
