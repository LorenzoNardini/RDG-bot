# RDG — Random Dinner Generator

A lightweight Telegram bot that generates random weekly dinner menus with progressive ingredient enrichment, reducing decision fatigue while maintaining variety and ingredient awareness.

**Status:** Production-ready (deployed on Railway)  
**Architecture:** Service-oriented with conversation handlers  
**Data Model:** SQLAlchemy ORM with SQLite (dev) / PostgreSQL (prod)  
**Test Coverage:** 46 tests (service layer + handler layer)

---

## System Overview

RDG Bot combines three core concerns:

1. **Menu Generation** — Randomized weekly meal plans with 7 positions, guaranteed category variety (1 meal per category for positions 1-6, free choice for position 7)
2. **External Ingredient Tracking** — Progressive enrichment of recipes with ingredients that must be sourced outside the regular online supermarket
3. **Shopping List Management** — Consolidated view of ingredients from recipes + temporary shopping reminders

The system is designed for **minimal friction** (mobile-first Telegram interface) and **progressive enrichment** (users gradually teach the bot which recipes need external sourcing).

---

## Features

### Core Menu Generation
- 🎲 **Random weekly menus** — Generates 7-day plans with one recipe from each of 6 categories (positions 1-6), one free-choice position (7)
- ♻️ **Smart reroll** — Change recipes by category (`/reroll pesce`) or by position (`/reroll 3`), with category constraints enforced for positions 1-6
- ♻️ **Batch reroll** — Change multiple positions at once (`/reroll 1 2 4`)
- 💾 **Menu history** — Save accepted menus; retrieve last 1 or last N menus (`/history` or `/history 3`)
- 📝 **Recipe management** — Add recipes, edit existing recipes (conversational flows)

### External Ingredients (Progressive Enrichment)
- **Status tracking** — Each recipe has `external_status`: "unknown" (default), "none" (no external ingredients), "defined" (has explicit ingredients)
- **Enrichment flow** — After `/accept`, bot checks which menu recipes are "unknown" and prompts user to clarify each one
- **Batch entry** — Enter multiple recipe ingredients in one message: `/external 1 salmon; 2 turmeric; 3 salt`
- **Single entry** — Or one at a time: `/external 1 salmon fillet, dill`
- **Skip entire flow** — User can `/skip` enrichment or `/noexternal 2 4` to mark specific recipes

### Shopping List Management
- **Consolidated list** — Unified view combining recipe external ingredients + temporary reminders
- **Temporary reminders** — Add items that don't belong to any recipe: `/remember coffee beans, batteries`
- **Clear when bought** — `/bought` clears all reminders and resets recipes to "unknown" for next enrichment cycle
- **View anytime** — `/remember` (no args) shows current consolidated shopping list

### List & Recipe Discovery
- **Filtered lists** — `/list` shows all recipes; `/list pesce` shows fish recipes
- **Ingredient labels** — `/ingredients` shows recipes grouped by external ingredient status
- **Find recipe** — `/edit "Recipe Name"` opens edit mode for a specific recipe

---

## Architecture

### Directory Structure

```
RDG Bot/
├── app/
│   ├── database/
│   │   ├── __init__.py
│   │   └── db.py                    # SQLAlchemy engine, session factory, migrations
│   ├── models/
│   │   ├── __init__.py
│   │   └── models.py                # ORM models
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── start.py                 # /start, /help (help text)
│   │   ├── roll.py                  # /roll
│   │   ├── reroll.py                # /reroll (category or position(s))
│   │   ├── accept.py                # /accept (saves menu, triggers enrichment)
│   │   ├── external.py              # /external, /noexternal, /skip (enrichment entry)
│   │   ├── fill_missing.py          # /fill_missing (manual enrichment of all unknown)
│   │   ├── history.py               # /history [n] (show last n menus)
│   │   ├── list_.py                 # /list [category]
│   │   ├── ingredients.py           # /ingredients (filter by external_status)
│   │   ├── add.py                   # /add (ConversationHandler for new recipes)
│   │   ├── edit.py                  # /edit (ConversationHandler for editing recipes)
│   │   ├── remember.py              # /remember [items] (shopping reminders)
│   │   └── bought.py                # /bought (clear reminders, reset recipes)
│   ├── services/
│   │   ├── __init__.py
│   │   ├── recipe_service.py        # CRUD + filtering for recipes
│   │   ├── menu_service.py          # Menu generation, reroll, accept logic
│   │   ├── external_service.py      # External ingredient status & storage
│   │   └── shopping_service.py      # Shopping reminder CRUD
│   └── utils/
│       ├── __init__.py
│       └── formatting.py            # Telegram message formatting
├── tests/
│   ├── test_services.py             # Service layer tests (30+ tests)
│   └── test_handlers.py             # Handler tests (16 tests)
├── data/
│   └── seed.py                      # One-time Excel → DB migration script
├── main.py                          # Bot entry point, handler registration
├── config.py                        # Environment config
├── requirements.txt
├── .env.example
├── RDG.xlsx                         # Excel source data (64 recipes)
└── README.md
```

### Technology Stack

- **Framework:** `python-telegram-bot` (v21+) with ConversationHandler for multi-step flows
- **ORM:** SQLAlchemy with declarative models
- **Database:** SQLite (dev) / PostgreSQL (prod), auto-migrated via SQLAlchemy
- **Testing:** pytest + pytest-asyncio for async handler testing
- **Deployment:** Railway (auto-deploy on git push to main)

---

## Data Model

### Core Models

#### Recipe
```python
class Recipe(Base):
    id: int (PK)
    name: str (unique)
    category: str  # one of: carne rossa, carne bianca, pesce, uova, legumi, altro
    needs_side: bool
    suggested_side: str (nullable)
    external_status: str  # "unknown" (default), "none", "defined"
    created_at: datetime
    updated_at: datetime
    
    # Relationships
    external_ingredients: List[ExternalIngredient]  # back-populated
```

**Design note:** `external_status` is a denormalized flag for fast filtering; `ExternalIngredient` table stores the actual ingredient list.

#### ExternalIngredient
```python
class ExternalIngredient(Base):
    id: int (PK)
    recipe_id: int (FK → Recipe.id, indexed)
    ingredient_name: str
    
    # Relationship
    recipe: Recipe
```

**Design note:** Simple 1:N relationship; each recipe can have multiple external ingredients.

#### ShoppingReminder
```python
class ShoppingReminder(Base):
    id: int (PK)
    item_name: str (unique)
    active: bool (default=True)
    created_at: datetime
```

**Design note:** Separate table from `ExternalIngredient` because reminders are user-typed, temporary items not tied to recipes.

#### WeeklyMenu
```python
class WeeklyMenu(Base):
    id: int (PK)
    created_at: datetime
    accepted_at: datetime (nullable)  # NULL = pending, set at /accept time
    
    # Relationship
    items: List[WeeklyMenuItem]
```

#### WeeklyMenuItem
```python
class WeeklyMenuItem(Base):
    id: int (PK)
    menu_id: int (FK → WeeklyMenu.id)
    recipe_id: int (FK → Recipe.id)
    position: int  # 1-7
    
    # Relationships
    menu: WeeklyMenu
    recipe: Recipe
```

---

## Service Layer

### RecipeService
**Responsibilities:** Recipe CRUD, filtering, category operations

**Key Methods:**
- `create(name, category, needs_side, suggested_side)` — Add recipe
- `get_by_name(name)` → Recipe | None
- `get_by_category(category)` → List[Recipe]
- `get_all()` → List[Recipe]
- `count_all()` → int
- `count_by_category(category)` → int
- `update(recipe_id, ...)` — Edit recipe fields

**Design:** Thin wrapper over ORM; no business logic, pure CRUD.

### MenuService
**Responsibilities:** Menu generation, reroll logic, state transitions

**Key Methods:**
- `generate_week()` → WeeklyMenu — Creates new pending menu with 7 items
  - Positions 1-6: One recipe per category (shuffled)
  - Position 7: Random recipe from any category, avoiding duplicates
- `get_menu_items(menu_id)` → List[WeeklyMenuItem] (ordered by position)
- `get_pending_menu(user_id_or_menu_id)` → WeeklyMenu | None
- `reroll_category(menu_id, category)` → bool — Replace all recipes of category
- `reroll_position(menu_id, position)` → bool
  - Positions 1-6: New recipe must be same category as old one (constraint enforcement)
  - Position 7: Any recipe allowed
- `reroll_positions(menu_id, positions: List[int])` → bool — Batch reroll
- `accept_menu(menu_id)` → None — Sets `accepted_at` timestamp
- `get_recent_accepted_menus(limit=5)` → List[WeeklyMenu] — For `/history`

**Design note:** Reroll logic validates category constraints before updating. Menu generation ensures no duplicates across the 7 positions.

### ExternalIngredientService
**Responsibilities:** Track & store ingredient enrichment data

**Key Methods:**
- `get_status(recipe_id)` → str — Returns "unknown" | "none" | "defined"
- `set_ingredients(recipe_id, ingredients: List[str])` → None
  - Deletes existing, inserts new, sets status to "defined"
- `set_no_external(recipe_id)` → None
  - Sets status to "none", clears any existing ingredients
- `get_ingredients(recipe_id)` → List[str]
- `get_unknown_recipes()` → List[Recipe] — All with status="unknown"
- `get_recipes_needing_enrichment(recipe_ids: List[int])` → List[Recipe] — Filter unknown from given set

**Design note:** Status is denormalized on Recipe for fast filtering; details stored in ExternalIngredient table.

### ShoppingReminderService
**Responsibilities:** Manage temporary shopping reminders

**Key Methods:**
- `add_reminders(items: List[str])` → int — Count added (skips duplicates)
- `get_active_reminders()` → List[str]
- `delete_reminder(item_name)` → bool
- `clear_reminders()` → int — Count cleared
- `count_active()` → int

**Design note:** Simple append-only list; `clear_reminders()` soft-deletes by setting `active=False` or hard-deletes depending on implementation.

---

## Handler Layer

### /roll
**Flow:**
1. Generate new menu with `MenuService.generate_week()`
2. Store menu_id in `context.user_data["pending_menu_id"]`
3. Format & display menu with positions and side dishes
4. Show reroll examples

**State:** Stores `pending_menu_id` for next reroll/accept

### /reroll
**Flow:**
1. Parse arguments: category name or position number(s)
2. Validate: positions 1-7 exist, categories are valid
3. For category: `MenuService.reroll_category(menu_id, category)`
4. For position(s): `MenuService.reroll_position(menu_id, position)` per position
5. Display updated menu

**Constraint enforcement:** Positions 1-6 maintain category; position 7 is free

### /accept
**Flow:**
1. `MenuService.accept_menu(pending_menu_id)` — Sets timestamp
2. Clear enrichment state from prior /accept attempts:
   - `context.user_data["enrichment_recipes"] = {}`
   - `context.user_data["enrichment_mode"] = None`
3. Get menu items and their recipes
4. Check external_status of each recipe
5. Collect recipes with status="unknown"
6. If any unknown:
   - Build `enrichment_recipes: {1: recipe_id, 2: recipe_id, ...}`
   - Store in context
   - Show enrichment prompt with `/external` batch syntax
7. If none: Confirm acceptance, done

**State:** Enrichment state stored in `context.user_data` for next `/external` or `/skip`

### /external
**Flow (batch mode):**
1. Parse: `/external 1 salmon; 2 turmeric; 3 salt`
2. For each number-ingredient pair:
   - Look up recipe_id from `context.user_data["enrichment_recipes"][number]`
   - `ExternalIngredientService.set_ingredients(recipe_id, [ingredients])`
   - Remove from enrichment_recipes dict
3. If enrichment_recipes still has items, re-show prompt
4. If empty, confirm & clear enrichment state

**Single mode:** Also accepts `/external 1 salmon, aneto` (comma-separated within one position)

**Slash handling:** Parser stops at next "/" to prevent command concatenation (`/external 1 item /reroll 2` only parses position 1)

### /noexternal
**Flow:**
1. Parse: `/noexternal 2 4` (position numbers)
2. For each position:
   - Look up recipe_id
   - `ExternalIngredientService.set_no_external(recipe_id)`
   - Remove from enrichment_recipes dict
3. Same cleanup as `/external`

**Batch support:** Multiple positions in one message

### /skip
**Flow:**
1. Clear `context.user_data["enrichment_recipes"]`
2. Confirm dismissal
3. User can manually use `/fill_missing` later to revisit

### /fill_missing
**Flow:**
1. `ExternalIngredientService.get_unknown_recipes()` → all recipes with status="unknown"
2. Build enrichment_recipes dict {1: id, 2: id, ...}
3. Show prompt with `/external` examples

### /remember
**Flow (no args):**
1. Collect all recipe external ingredients where status="defined"
2. Get active shopping reminders
3. Consolidate into one list (deduplicate, sort)
4. Format with emoji: "🛒 Remember to buy:\n  • item1\n  • item2"
5. Show

**Flow (with args):**
1. Parse: `/remember coffee beans, batteries`
2. `ShoppingReminderService.add_reminders(items)`
3. Get updated consolidated list
4. Format & show

### /bought
**Flow:**
1. Count active reminders & recipes with external_status != "unknown"
2. `ShoppingReminderService.clear_reminders()`
3. Reset all recipes with status != "unknown" back to "unknown"
4. Show confirmation with count

**Workflow:** Enables progressive re-enrichment; user buys items, marks as bought, next time they accept a menu with the same recipes, they'll be asked again (in case preferences changed)

### /history [n]
**Flow:**
1. Parse optional argument `n` (default=1)
2. Validate: positive integer, max 10
3. `MenuService.get_recent_accepted_menus(limit=n)`
4. For each menu:
   - Show date accepted
   - Format menu with category grouping
   - Show external ingredients per recipe (if status="defined")
5. Show active shopping reminders + prompt to use `/remember`

### /list [category]
**Flow:**
1. If category provided: filter recipes
2. Validate category exists
3. Format grouped by category with emojis
4. Show

**Multi-word support:** Joins args with space: `/list carne bianca` → category="carne bianca"

### /add (ConversationHandler)
**States:**
1. `ADD_NAME` — User enters recipe name
2. `ADD_CATEGORY` — User selects from category list
3. `ADD_NEEDS_SIDE` — Yes/No for side dish
4. `ADD_SIDE` (conditional) — User enters side name if needs_side=True
5. Save & confirm

**Design:** Telegram ConversationHandler manages state flow; simple numbered menu for category selection

### /edit (ConversationHandler)
**Flow:**
1. Ask user for recipe name to edit
2. Load recipe, show current values in numbered menu
3. User selects field to edit
4. User enters new value
5. Save & confirm

**Editable fields:** name, category, needs_side, suggested_side, external_ingredients (text field)

### /ingredients
**Flow:**
1. `ExternalIngredientService.get_unknown_recipes()`
2. `ExternalIngredientService.get_recipes_needing_enrichment(all_recipe_ids)` (status="defined" or "none")
3. Format with status indicators:
   - Unknown recipes: no label
   - status="none": ✅ No external ingredients needed
   - status="defined": 🛒 ingredient list
4. Show grouped by category

---

## Conversation State Management

### Context Structure (context.user_data)

```python
context.user_data = {
    "pending_menu_id": 42,  # Active menu for /reroll, /accept
    
    # Enrichment flow (cleared at /accept start, set at /accept end)
    "enrichment_recipes": {1: recipe_id, 2: recipe_id, ...},
    "enrichment_mode": None,  # Future use for different enrichment contexts
    "enrichment_index": None,  # Future use for guided step-by-step
}
```

**Design decision:** State stored in memory (dict) not in database because:
- Menus are typically accepted within one conversation session
- Enrichment data is temporary (user switches contexts, menu expires)
- Single-user MVP; no user ID needed

**Trade-off:** State lost on bot restart. For production multi-user, would store in database with user_id keyed to Telegram user ID.

---

## Menu Generation Algorithm

### Guarantee Variety
```
1. Shuffle categories: [pesce, legumi, carne rossa, uova, carne bianca, altro]
2. For each category in shuffled order:
   - Pick random recipe from category
   - Assign to position (1-6)
3. Fill position 7:
   - Pick random recipe from any category
   - Ensure not already in menu
```

### Reroll Constraints
- **Positions 1-6:** Must maintain category (category constraint)
- **Position 7:** Any category allowed (free choice)
- **No duplicates:** Within same menu, no recipe appears twice

### Implementation (MenuService.reroll_position)
```
if position in [1, 6]:
    old_category = current_recipe.category
    new_recipe = random from (old_category) - {current_recipe}
else:  # position 7
    new_recipe = random from (any) - {recipes_in_menu}
```

---

## External Ingredients Workflow

### Progressive Enrichment Philosophy
- **Default:** All recipes start as "unknown"
- **Optional:** User gradually teaches bot which recipes need external sourcing
- **Non-blocking:** User can skip enrichment, accept menu without answering
- **Revisable:** `/fill_missing` shows all unknown recipes; `/bought` resets for next cycle

### State Transitions
```
Recipe created → external_status="unknown"
                ↓
User accepts menu with recipe → prompt if unknown
                ↓
User enters /external → status="defined"
           or /noexternal → status="none"
           or /skip → stays "unknown"
                ↓
User /bought → resets to "unknown"
```

### Consolidated Shopping List
```
Recipe ingredients (status="defined") + temporary reminders
↓ Deduplicate (set)
↓ Sort alphabetically
↓ Format with emoji + bullet list
```

---

## Testing Strategy

### Test Structure
```
tests/
├── test_services.py
│   ├── TestRecipeService (CRUD, filtering)
│   ├── TestMenuService (generation, reroll, accept)
│   ├── TestExternalIngredientService (status, ingredients)
│   ├── TestShoppingReminderService (reminders)
│   ├── TestConsolidatedShoppingList (formatting)
│   └── TestBoughtCommand (reset logic)
└── test_handlers.py
    ├── TestRememberHandler (shopping list)
    ├── TestBoughtHandler (clear & reset)
    ├── TestListHandler (filtering)
    ├── TestHistoryHandler (pagination)
    ├── TestExternalHandler (parsing)
    └── TestRerollHandler (constraints)
```

### Coverage
- **Service layer:** 30+ tests covering CRUD, state transitions, constraints
- **Handler layer:** 16+ tests covering argument parsing, state flow, error cases
- **Total:** 46 tests, all passing

### Test Database
- In-memory SQLite (`:memory:`) for speed
- Fixtures: `test_db` (fresh database per test), `seed_recipes` (8 test recipes)
- Async handlers mocked with `unittest.mock` + `patch`

---

## Key Design Decisions

### 1. Menu Generation: Pure Randomness
**Why:** Reduce decision fatigue, not overthink meals  
**Trade-off:** No user preferences, ratings, or seasonal adjustments  
**Future:** Could add tags (vegetarian, quick, expensive) and filter by user preference

### 2. External Ingredients: Progressive Enrichment
**Why:** Reduce data entry friction upfront; let users teach the bot over time  
**Trade-off:** Incomplete data in early weeks; requires user discipline  
**Benefit:** User learns what they need; data gets richer over time

### 3. Shopping List: Consolidated View
**Why:** User doesn't care whether ingredient is from recipe or reminder; single source of truth  
**Trade-off:** Lost information about source (recipe vs. reminder)  
**Future:** Could add source indicators if needed

### 4. Conversation State: In-Memory Dict
**Why:** Simple, fast, sufficient for single-user MVP  
**Trade-off:** Lost on bot restart; not scalable to multi-user  
**Future:** Migrate to database with user_id for production scale

### 5. Category Constraints: Positions 1-6 Only
**Why:** Ensure variety while allowing flexibility for position 7 (special theme night)  
**Trade-off:** Reroll positions 1-6 can fail if only 1 recipe in category  
**Future:** Add fallback logic (allow duplicate if no alternatives)

### 6. Slash Parsing: Stop at Next "/"
**Why:** Prevent accidental command concatenation (user types multiple commands)  
**Design:** `/external 1 item /reroll 2` only parses position 1  
**Trade-off:** Unclear error if user meant to send two messages

---

## Deployment

### Current Setup
- **Hosting:** Railway (auto-deploy on git push to main)
- **Polling:** `run_polling()` with message updates
- **Database:** PostgreSQL on Railway
- **Environment:** .env with BOT_TOKEN, DATABASE_URL

### Monitoring
- Check bot health: Send test message to bot on Railway dashboard
- View logs: Railway dashboard logs tab
- Database: Railway PostgreSQL data browser

### Future: Webhooks
Current code uses polling. For higher volume, switch to webhooks:
```python
# main.py
app.run_webhook(listen="0.0.0.0", port=PORT, url_path="/webhook", webhook_url=f"{WEBHOOK_URL}/webhook")
```

---

## Limitations & Future Features

### Current Limitations
1. **Single-user:** Conversation state not keyed to user ID (works for personal bot only)
2. **No persistence of enrichment flow:** If user closes chat mid-enrichment, state is lost
3. **No recipe ratings or usage frequency:** Pure randomness, no learning
4. **No multi-language:** Italian labels only
5. **No dish complexity levels:** All recipes treated equally

### Potential Enhancements
1. **User profiles:** Track user preferences, dietary restrictions, allergies
2. **Persistent enrichment:** Store in-progress enrichment in database
3. **Recipe analytics:** Track which recipes accepted vs. rerolled; suggest popular ones
4. **Category expansion:** Add seasonal categories, prep-time tiers
5. **Meal planning:** Multi-week plans, export to calendar
6. **Grocery integration:** Link to online supermarket pricing
7. **Rate limiting:** Prevent bot abuse
8. **Admin commands:** Bulk recipe import, user management, analytics dashboard
9. **Multi-language:** Support Italian, English, others
10. **ConversationHandler improvements:** Fallback states for unexpected input

---

## Development Workflow

### Adding a New Feature

**Example: Add recipe filtering by prep time**

1. **Database migration:** Add `prep_time_minutes: int` column to Recipe
2. **Service layer:** Add `get_by_prep_time(max_minutes)` to RecipeService
3. **Handler:** Create `/quick` command that uses new service method
4. **Tests:** Write tests for service method + handler
5. **Help text:** Update `/help` in start.py
6. **Commit & deploy:** Push to main; Railway auto-deploys

### Code Style
- **Services:** Pure business logic, no Telegram references
- **Handlers:** Thin wrapper; orchestrate services + format output
- **Formatting:** All Telegram-specific markup in `utils/formatting.py`
- **Tests:** One test file per module; fixtures in conftest or file-local

---

## Commands Reference (Quick Lookup)

| Command | Args | Purpose |
|---------|------|---------|
| `/start` | | Show help |
| `/help` | | Show all commands |
| `/roll` | | Generate menu |
| `/reroll` | `<category\|position...>` | Change recipe(s) |
| `/accept` | | Save menu, start enrichment |
| `/external` | `<N> ingredient...` | Set external ingredients |
| `/noexternal` | `<N...>` | Mark recipes as having no external ingredients |
| `/skip` | | Skip enrichment |
| `/fill_missing` | | Show all unknown recipes |
| `/history` | `[n]` | Show last n menus (default 1) |
| `/list` | `[category]` | Show recipes |
| `/ingredients` | | Show by external ingredient status |
| `/add` | | Add new recipe |
| `/edit` | `"name"` | Edit recipe |
| `/remember` | `[items]` | View/add shopping reminders |
| `/bought` | | Clear reminders & reset recipes |

---

## Troubleshooting for Architects

### Common Issues

**Q: Bot doesn't respond**  
A: Check Railway logs for exceptions. Verify BOT_TOKEN is set and valid.

**Q: Menu generation is slow**  
A: Typically <100ms. If slow, check database query performance (ensure indexes on recipe.category).

**Q: Enrichment prompt doesn't show after /accept**  
A: Verify `accept.py` is clearing `enrichment_recipes` at start. Check that recipes have `external_status` column.

**Q: Reroll fails on position 1-6**  
A: Likely only one recipe in that category. Add more recipes to category or enhance fallback logic in MenuService.

**Q: External ingredients lost after /bought**  
A: This is intentional. `/bought` resets `external_status` to "unknown" for progressive re-enrichment.

---

## File Structure Notes

### Why models.py is Single File
All ORM models in one file for simplicity; imports are centralized. If >10 models, consider splitting by domain (menu.py, recipe.py, etc.).

### Why handlers are Individual Files
One handler per command for clarity; makes ConversationHandlers self-contained. Easy to find and modify.

### Why services are Separate Classes
Each service handles one domain (recipes, menus, ingredients, reminders); encapsulates business logic; testable in isolation.

---

## Next Steps for New Features

1. **Read CLAUDE.md** in project root for development notes
2. **Review test suite** to understand expected behavior
3. **Check memory.md** for prior discussion context
4. **Sketch domain changes** (new tables, service methods)
5. **Write tests first** (TDD); implement features
6. **Update help text** in start.py
7. **Deploy to Railway** and test with real bot

---

## License

Personal project. Use freely for learning and adaptation.

---

## Contact / Feedback

Built for personal meal planning workflow. Open to architectural suggestions and feature requests.
