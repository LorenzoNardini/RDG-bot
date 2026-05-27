# External Ingredients Feature

A lightweight system for tracking which recipe ingredients must be purchased outside the online supermarket (fish market, butcher, specialty stores, etc).

## Overview

When you accept a weekly menu with `/accept`, the bot checks which recipes don't yet have external ingredient information. It gently prompts you to enrich the database over time—but you can `/skip` if you're not in the mood.

This is **intentionally lightweight**: no complex ingredient ontology, no quantities, no AI parsing—just a simple list of ingredients that need special sourcing.

## New Commands

### `/external <number> ingredient1, ingredient2, ...`
Mark external ingredients for a recipe in the current enrichment list.

**Example:**
```
/external 1 salmon fillet, dill
```

**Response:**
```
✅ Salmon with honey mustard
External ingredients: salmon fillet, dill
```

### `/noexternal <number>`
Mark a recipe as having no external ingredients required.

**Example:**
```
/noexternal 2
```

**Response:**
```
✅ Chickpea soup
No external ingredients needed.
```

### `/skip`
Dismiss the current enrichment session without blocking workflow.

**Example:**
```
/skip
```

**Response:**
```
Skipped enrichment. You can always use /fill_missing later to improve the database.
```

### `/fill_missing`
Start a dedicated enrichment mode. Shows all recipes with unknown external ingredient status.

**Example:**
```
/fill_missing
```

**Response:**
```
🛒 External ingredient information missing

I still don't know whether these recipes require ingredients purchased outside the online supermarket:

1. Fish curry
2. Lentil soup
3. Fried rice

Reply with:
• /external 1 salmon fillet, turmeric
• /noexternal 2
• /skip
```

## Workflow

### After /accept (Automatic)

1. User runs `/accept` to save weekly menu
2. Bot saves menu to history
3. Bot checks which recipes in that week have unknown external ingredient status
4. If any recipes are unknown:
   - Shows menu confirmation
   - Appends enrichment prompt with numbered list
   - Stores enrichment mapping in session
5. User can respond immediately with `/external`, `/noexternal`, or `/skip`
6. Or ignore and come back with `/fill_missing` later

### Manual Enrichment

1. Run `/fill_missing` anytime
2. Bot shows all recipes with unknown status
3. Respond with `/external` and `/noexternal` as desired
4. When done, run `/fill_missing` again — should see fewer recipes

## Data Model

### Recipe Updates
- New column: `external_status` (String) with values:
  - `"unknown"` — not yet assessed (default)
  - `"none"` — confirmed no external ingredients
  - `"defined"` — has explicit external ingredients saved

### New Table: external_ingredients
```
id (PK)
recipe_id (FK → recipes)
ingredient_name (String)
```

One recipe can have multiple external ingredients.

## Architecture

### New Service: ExternalIngredientService
**Location:** `app/services/external_service.py`

Methods:
- `get_status(recipe_id)` — returns current status
- `set_ingredients(recipe_id, ingredients)` — save ingredients, mark as "defined"
- `set_no_external(recipe_id)` — mark as "none"
- `get_ingredients(recipe_id)` — retrieve ingredient list
- `get_unknown_recipes()` — all recipes needing enrichment
- `get_recipes_needing_enrichment(recipe_ids)` — filter a list to unknowns

### New Handlers
- `app/handlers/external.py` — `/external`, `/noexternal`, `/skip`
- `app/handlers/fill_missing.py` — `/fill_missing`

### Modified Handler
- `app/handlers/accept.py` — now triggers enrichment after menu acceptance

### Formatting
- `app/utils/formatting.py` — new `format_enrichment_prompt()` function

## UX Principles

✅ **What this feature is:**
- Fast to use
- Non-blocking (can skip anytime)
- Conversational
- Optional
- Progressive (build database gradually)

❌ **What this feature is NOT:**
- A full recipe / ingredient system
- Meal planning with quantities
- Nutritional tracking
- AI-powered
- Pushy or mandatory

## Testing

```bash
# Start bot locally
python main.py

# Test workflow:
1. /roll → generate menu
2. /accept → should see enrichment prompt for unknown recipes
3. /external 1 salmon, dill → confirm recipe updated
4. /noexternal 2 → confirm recipe updated
5. /skip → dismiss
6. /fill_missing → see remaining unknown recipes
7. Accept another menu → enrichment prompt only for new unknowns
```

## Future Extensions

The architecture supports (but doesn't yet implement):
- Store categories (fish markets, butchers, etc)
- Ingredient quantities
- Aggregated shopping list generation
- Sourcing tips or preferred vendor notes
- Integration with online supermarket APIs

Keep the current simplicity; only add complexity when needed.

## Database Migration

The feature includes automatic migration:
- On bot startup, `init_db()` calls `_migrate_db()`
- Adds `external_status` column to recipes if not present
- Creates `external_ingredients` table
- Safe to run multiple times (idempotent)

## Notes

- Enrichment numbers (1, 2, 3...) shown in enrichment prompts are **independent** of menu positions (1-7 days)
- Session state is stored in `context.user_data["enrichment_recipes"]` — survives during a Telegram session
- Each recipe can have multiple external ingredients (list)
- No limit on ingredient list length (intentionally simple)
