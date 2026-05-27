import logging
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
)
from config import BOT_TOKEN
from app.database.db import init_db
from app.handlers.start import start, help_command
from app.handlers.roll import roll
from app.handlers.reroll import reroll
from app.handlers.accept import accept
from app.handlers.list_ import list_recipes
from app.handlers.history import history
from app.handlers.add import get_add_handler

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def main():
    """Run the bot."""
    # Initialize database
    init_db()
    logger.info("Database initialized.")

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

    # Register conversation handler for /add
    app.add_handler(get_add_handler())

    # Start the bot
    logger.info("Starting bot...")
    app.run_polling(allowed_updates=["message", "edited_message"])


if __name__ == "__main__":
    main()
