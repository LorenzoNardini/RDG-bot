#!/usr/bin/env python3
"""
One-time migration to fix out-of-sync external_status.

Issue: external_ingredients table has data, but recipes.external_status
wasn't updated. This script syncs them.

Run this ONCE on Railway: heroku run python scripts/fix_external_status_sync.py

Or if running locally, it will use the local SQLite database.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database.db import get_session
from app.models.models import Recipe, ExternalIngredient

def fix_external_status():
    """Fix recipes that have external_ingredient records but wrong status."""
    session = get_session()

    try:
        # Find all recipes with external_ingredient records
        recipes_with_ingredients = session.query(Recipe).join(
            ExternalIngredient
        ).distinct().all()

        print(f"Found {len(recipes_with_ingredients)} recipes with external ingredients")

        # Update their status to "defined"
        fixed_count = 0
        for recipe in recipes_with_ingredients:
            if recipe.external_status != "defined":
                print(f"  Fixing: {recipe.name} (was '{recipe.external_status}', now 'defined')")
                recipe.external_status = "defined"
                fixed_count += 1

        if fixed_count > 0:
            session.flush()  # Ensure all updates are persisted
            session.commit()
            print(f"\n[SUCCESS] Fixed {fixed_count} recipes!")
        else:
            print("\n[OK] All recipes are already synced!")

    except Exception as e:
        print(f"[ERROR] {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    fix_external_status()
