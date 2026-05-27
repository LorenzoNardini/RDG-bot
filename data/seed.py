"""
Seed script to import recipes from RDG.xlsx into the database.
Run this once to populate the recipes table.
"""
import openpyxl
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database.db import get_session, init_db
from app.services.recipe_service import RecipeService


def seed_recipes(excel_path: str):
    """Read recipes from RDG.xlsx and insert into database."""
    # Initialize database
    init_db()
    session = get_session()

    try:
        recipe_service = RecipeService(session)

        # Load Excel file
        print(f"Loading recipes from {excel_path}...")
        wb = openpyxl.load_workbook(excel_path)
        ws = wb["Ricette"]

        # Skip header row (row 1)
        recipes_added = 0
        recipes_skipped = 0

        for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            if not row[0]:  # Skip empty rows
                continue

            name = row[0].strip() if row[0] else None
            category = row[1].strip().lower() if row[1] else None
            needs_side_text = row[2] if row[2] else "No"
            side = row[7].strip() if len(row) > 7 and row[7] else None

            # Validate
            if not name or not category:
                print(f"  [skip] Row {row_idx}: Missing name or category")
                recipes_skipped += 1
                continue

            # Parse needs_side
            needs_side = needs_side_text.lower() in ["sì", "yes", "s", "true"]

            # Check if recipe already exists
            existing = recipe_service.get_by_name(name)
            if existing:
                print(f"  [exists] {name}")
                recipes_skipped += 1
                continue

            # Create recipe
            try:
                recipe = recipe_service.create(
                    name=name,
                    category=category,
                    needs_side=needs_side,
                    suggested_side=side
                )
                print(f"  [added] {name} ({category})")
                recipes_added += 1
            except Exception as e:
                print(f"  [error] {name}: {e}")
                recipes_skipped += 1

        print(f"\n[done] Seeding complete!")
        print(f"  Added: {recipes_added}")
        print(f"  Skipped: {recipes_skipped}")
        total = recipe_service.count_all()
        print(f"  Total in DB: {total}")

    finally:
        session.close()


if __name__ == "__main__":
    # Find Excel file
    current_dir = Path(__file__).parent.parent
    excel_path = current_dir / "RDG.xlsx"

    if not excel_path.exists():
        print(f"❌ Excel file not found: {excel_path}")
        sys.exit(1)

    seed_recipes(str(excel_path))
