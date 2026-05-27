"""
Quick test to verify bot core logic works.
Tests menu generation, rerolling, and formatting.
"""
import sys
from pathlib import Path

from app.database.db import get_session, init_db
from app.services.menu_service import MenuService
from app.services.recipe_service import RecipeService
from app.utils.formatting import format_menu

init_db()
session = get_session()

try:
    recipe_service = RecipeService(session)
    menu_service = MenuService(session)

    print("Testing RDG Bot Logic")
    print("=" * 60)

    # Test 1: Count recipes
    total = recipe_service.count_all()
    print(f"\n[Test 1] Recipe count: {total}")
    assert total > 0, "No recipes in database!"
    print("  PASS")

    # Test 2: Count by category
    print("\n[Test 2] Recipes per category:")
    for category in ["carne rossa", "carne bianca", "pesce", "uova", "legumi", "altro"]:
        count = recipe_service.count_by_category(category)
        print(f"  {category}: {count}")
        assert count > 0, f"No recipes in {category}!"
    print("  PASS")

    # Test 3: Generate menu
    print("\n[Test 3] Generate weekly menu...")
    menu = menu_service.generate_week()
    assert menu is not None, "Failed to generate menu!"
    assert menu.id is not None, "Menu has no ID!"
    print(f"  Generated menu ID: {menu.id}")
    print("  PASS")

    # Test 4: Get menu items
    print("\n[Test 4] Get menu items...")
    items = menu_service.get_menu_items(menu.id)
    assert len(items) == 7, f"Expected 7 items, got {len(items)}"
    print(f"  Items: {len(items)}")
    for item in items:
        print(f"    {item.position}. {item.recipe.name} ({item.recipe.category})")
    print("  PASS")

    # Test 5: Format menu for Telegram
    print("\n[Test 5] Format menu for Telegram...")
    formatted = format_menu(menu, items)
    # Just verify it formats without error, don't print emojis to console
    assert len(formatted) > 0, "Menu formatting failed!"
    assert "Menu" in formatted, "Menu title missing!"
    print(f"  Formatted menu: {len(formatted)} characters")
    print("  PASS")

    # Test 6: Reroll by position
    print("\n[Test 6] Reroll position 3...")
    original_recipe = items[2].recipe.name
    menu_service.reroll_position(menu.id, 3)
    items = menu_service.get_menu_items(menu.id)
    new_recipe = items[2].recipe.name
    assert original_recipe != new_recipe, "Reroll didn't change recipe!"
    print(f"  Changed from '{original_recipe}' to '{new_recipe}'")
    print("  PASS")

    # Test 7: Reroll by category
    print("\n[Test 7] Reroll category 'pesce'...")
    items_before = menu_service.get_menu_items(menu.id)
    pesce_item_before = next((i for i in items_before if i.recipe.category == "pesce"), None)
    if pesce_item_before:
        original_recipe = pesce_item_before.recipe.name
        menu_service.reroll_category(menu.id, "pesce")
        items_after = menu_service.get_menu_items(menu.id)
        pesce_item_after = next((i for i in items_after if i.recipe.category == "pesce"), None)
        new_recipe = pesce_item_after.recipe.name
        assert original_recipe != new_recipe, "Reroll didn't change recipe!"
        print(f"  Changed from '{original_recipe}' to '{new_recipe}'")
        print("  PASS")
    else:
        print("  SKIP (pesce not in menu)")

    # Test 8: Accept menu
    print("\n[Test 8] Accept menu...")
    assert menu.is_pending(), "Menu is not pending!"
    menu_service.accept_menu(menu.id)
    menu = menu_service.get_menu(menu.id)
    assert menu.is_accepted(), "Menu not marked as accepted!"
    print("  PASS")

    # Test 9: Get history
    print("\n[Test 9] Get recent accepted menus...")
    recent = menu_service.get_recent_accepted_menus(limit=3)
    print(f"  Found {len(recent)} accepted menus")
    print("  PASS")

    print("\n" + "=" * 60)
    print("All tests passed! Bot is ready to deploy.")

finally:
    session.close()
