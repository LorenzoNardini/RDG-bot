from sqlalchemy.orm import Session
from app.models.models import Recipe


class RecipeService:
    def __init__(self, session: Session):
        self.session = session

    def create(self, name: str, category: str, needs_side: bool = False, suggested_side: str = None) -> Recipe:
        """Create a new recipe."""
        recipe = Recipe(
            name=name,
            category=category,
            needs_side=needs_side,
            suggested_side=suggested_side
        )
        self.session.add(recipe)
        self.session.commit()
        self.session.refresh(recipe)
        return recipe

    def get_by_id(self, recipe_id: int) -> Recipe | None:
        """Get recipe by ID."""
        return self.session.query(Recipe).filter(Recipe.id == recipe_id).first()

    def get_by_name(self, name: str) -> Recipe | None:
        """Get recipe by name (case-insensitive)."""
        return self.session.query(Recipe).filter(Recipe.name.ilike(name)).first()

    def get_all(self) -> list[Recipe]:
        """Get all recipes."""
        return self.session.query(Recipe).all()

    def get_by_category(self, category: str) -> list[Recipe]:
        """Get all recipes in a category."""
        return self.session.query(Recipe).filter(Recipe.category == category).all()

    def search(self, query: str) -> list[Recipe]:
        """Search recipes by name (case-insensitive substring)."""
        return self.session.query(Recipe).filter(Recipe.name.ilike(f"%{query}%")).all()

    def count_by_category(self, category: str) -> int:
        """Count recipes in a category."""
        return self.session.query(Recipe).filter(Recipe.category == category).count()

    def count_all(self) -> int:
        """Count total recipes."""
        return self.session.query(Recipe).count()

    def delete(self, recipe_id: int) -> bool:
        """Delete a recipe."""
        recipe = self.get_by_id(recipe_id)
        if recipe:
            self.session.delete(recipe)
            self.session.commit()
            return True
        return False
