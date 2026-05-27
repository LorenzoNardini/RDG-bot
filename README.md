# RDG — Random Dinner Generator

A lightweight Telegram bot that generates random weekly dinner menus, helping reduce decision fatigue while maintaining variety.

## Features

- 🎲 **Random weekly menus** - Generates 7-day plans with one recipe from each main category
- ♻️ **Smart reroll** - Change specific meals or entire categories
- 💾 **Menu history** - Saves accepted menus for future reference
- 📝 **Recipe management** - Add new recipes with categories and side suggestions
- 🚀 **Fast & conversational** - Mobile-first Telegram interface, minimal friction

## Installation

### Prerequisites

- Python 3.12+
- A Telegram Bot Token (create via [@BotFather](https://t.me/botfather))

### Setup

1. **Clone/Navigate to project**
   ```bash
   cd "RDG Bot"
   ```

2. **Create virtual environment** (optional but recommended)
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env and add your BOT_TOKEN
   ```

5. **Seed initial recipes** (one-time)
   ```bash
   python data/seed.py
   ```

6. **Run the bot**
   ```bash
   python main.py
   ```

## Commands

### User Commands

| Command | Usage | Description |
|---------|-------|-------------|
| `/start` | | Start the bot and see help |
| `/help` | | Show all commands |
| `/roll` | | Generate a new weekly menu |
| `/reroll` | `<category\|position>` | Change a meal: `/reroll pesce` or `/reroll 3` |
| `/accept` | | Save the current menu to history |
| `/list` | `[category]` | Show all recipes or filter by category |
| `/add` | | Add a new recipe (conversational) |
| `/history` | | Show recently accepted menus |

### Workflow Example

```
1. /roll                  → Get 7-day menu
2. /reroll pesce         → Change the fish meal
3. /reroll 3             → Change position 3
4. /accept               → Save and finish
```

## Architecture

```
RDG Bot/
├── app/
│   ├── database/        # SQLAlchemy setup
│   ├── models/          # ORM models (Recipe, WeeklyMenu, WeeklyMenuItem)
│   ├── handlers/        # Telegram command handlers
│   ├── services/        # Business logic (MenuService, RecipeService)
│   └── utils/           # Formatting helpers
├── data/
│   └── seed.py          # Excel import script
├── main.py              # Bot entry point
├── config.py            # Configuration via .env
└── requirements.txt
```

## Database Schema

### Recipes
- `id`, `name` (unique), `category`, `needs_side`, `suggested_side`
- Future fields: `tags`, `prep_time`, `difficulty`, `last_used`, `rating`

### Weekly Menus
- `id`, `created_at`, `accepted_at` (NULL = pending)

### Weekly Menu Items
- `id`, `menu_id`, `recipe_id`, `position` (1-7)

## Menu Generation Logic

1. **Guarantee variety**: Pick 1 recipe from each of 6 categories
2. **Fill remaining slot**: Random recipe from any category (avoiding duplicates)
3. **Pure randomness**: No AI, no scoring, user manually rerolls until satisfied
4. **Pending until accept**: Menu stored but not in history until `/accept`

## Recipe Categories

- 🥩 Carne rossa (Red meat)
- 🍗 Carne bianca (White meat)
- 🐟 Pesce (Fish)
- 🥚 Uova (Eggs)
- 🫘 Legumi (Legumes)
- 🍝 Altro (Other)

## Configuration

### .env Variables

```env
BOT_TOKEN=your_telegram_bot_token
DATABASE_URL=sqlite:///./rdg_bot.db
```

### Database

Default is SQLite (`rdg_bot.db`). For production, use PostgreSQL:
```env
DATABASE_URL=postgresql://user:password@localhost/rdg_bot
```

## Development

### Add a New Command

1. Create handler in `app/handlers/my_command.py`
2. Register in `main.py`:
   ```python
   app.add_handler(CommandHandler("mycommand", my_command))
   ```

### Add a New Recipe

```python
from app.database.db import get_session
from app.services.recipe_service import RecipeService

session = get_session()
service = RecipeService(session)
recipe = service.create(
    name="Lasagna al ragù",
    category="altro",
    needs_side=False
)
```

## Deployment

### Telegram Polling (Simple, for testing)
```bash
python main.py
```

### Webhooks (Production)
Update `main.py` to use `run_webhook()` instead of `run_polling()`.

### Hosting Options

- **Railway**: `railway.app`
- **Render**: `render.com`
- **Fly.io**: `fly.io`
- **VPS/Raspberry Pi**: Direct SSH deployment

## Troubleshooting

### Bot doesn't respond
- Check BOT_TOKEN in `.env`
- Run: `python main.py` and watch for errors
- Verify Telegram @BotFather created the token correctly

### Recipes not loading
- Run `python data/seed.py`
- Check that `RDG.xlsx` exists in project root

### Database errors
- Delete `rdg_bot.db` and rerun `python data/seed.py`
- Check database URL in `.env`

## License

Personal project. Use freely.

## Notes

- Single-user MVP (context stored in memory per user)
- Menu history persists in database
- All operations are reversible until `/accept`
- No external API calls or dependencies (except Telegram API)
