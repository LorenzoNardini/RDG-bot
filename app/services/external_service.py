from sqlalchemy.orm import Session
from app.models.models import Recipe, ExternalIngredient


class ExternalIngredientService:
    def __init__(self, session: Session):
        self.session = session

    def get_status(self, recipe_id: int) -> str:
        """Get external ingredient status for a recipe."""
        recipe = self.session.query(Recipe).filter(Recipe.id == recipe_id).first()
        if not recipe:
            return "unknown"
        return recipe.external_status

    def set_ingredients(self, recipe_id: int, ingredients: list[str]) -> bool:
        """Set external ingredients for a recipe and mark as 'defined'."""
        recipe = self.session.query(Recipe).filter(Recipe.id == recipe_id).first()
        if not recipe:
            return False

        # Delete existing ingredients
        self.session.query(ExternalIngredient).filter(
            ExternalIngredient.recipe_id == recipe_id
        ).delete()

        # Add new ingredients
        for ingredient in ingredients:
            ext_ing = ExternalIngredient(
                recipe_id=recipe_id,
                ingredient_name=ingredient.strip()
            )
            self.session.add(ext_ing)

        # Update status
        recipe.external_status = "defined"
        self.session.commit()
        return True

    def set_no_external(self, recipe_id: int) -> bool:
        """Mark recipe as having no external ingredients."""
        recipe = self.session.query(Recipe).filter(Recipe.id == recipe_id).first()
        if not recipe:
            return False

        # Delete existing ingredients
        self.session.query(ExternalIngredient).filter(
            ExternalIngredient.recipe_id == recipe_id
        ).delete()

        # Update status
        recipe.external_status = "none"
        self.session.commit()
        return True

    def get_ingredients(self, recipe_id: int) -> list[str]:
        """Get list of external ingredients for a recipe."""
        ingredients = self.session.query(ExternalIngredient).filter(
            ExternalIngredient.recipe_id == recipe_id
        ).all()
        return [ing.ingredient_name for ing in ingredients]

    def get_unknown_recipes(self) -> list[Recipe]:
        """Get all recipes with unknown external ingredient status."""
        return self.session.query(Recipe).filter(
            Recipe.external_status == "unknown"
        ).order_by(Recipe.name).all()

    def get_recipes_needing_enrichment(self, recipe_ids: list[int]) -> list[Recipe]:
        """Filter recipes from a list to only those with unknown status."""
        if not recipe_ids:
            return []
        return self.session.query(Recipe).filter(
            Recipe.id.in_(recipe_ids),
            Recipe.external_status == "unknown"
        ).order_by(Recipe.name).all()
