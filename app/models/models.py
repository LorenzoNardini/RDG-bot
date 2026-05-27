from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database.db import Base


class Recipe(Base):
    __tablename__ = "recipes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    category = Column(String, index=True, nullable=False)  # carne rossa, carne bianca, pesce, uova, legumi, altro
    needs_side = Column(Boolean, default=False)
    suggested_side = Column(String, nullable=True)

    # Future fields (structured for extensibility)
    tags = Column(String, nullable=True)  # Comma-separated
    prep_time = Column(Integer, nullable=True)  # Minutes
    difficulty = Column(String, nullable=True)  # easy, medium, hard
    last_used = Column(DateTime, nullable=True)
    rating = Column(Integer, nullable=True)  # 1-5

    external_status = Column(String, default="unknown")  # unknown | none | defined

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    menu_items = relationship("WeeklyMenuItem", back_populates="recipe", cascade="all, delete-orphan")
    external_ingredients = relationship("ExternalIngredient", back_populates="recipe", cascade="all, delete-orphan")

    def __repr__(self):
        return f"Recipe(id={self.id}, name='{self.name}', category='{self.category}')"


class WeeklyMenu(Base):
    __tablename__ = "weekly_menus"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    accepted_at = Column(DateTime, nullable=True)  # None = pending, set when /accept is called

    # Relationship
    items = relationship("WeeklyMenuItem", back_populates="menu", cascade="all, delete-orphan")

    def __repr__(self):
        status = "accepted" if self.accepted_at else "pending"
        return f"WeeklyMenu(id={self.id}, status={status}, created_at={self.created_at})"

    def is_accepted(self):
        return self.accepted_at is not None

    def is_pending(self):
        return self.accepted_at is None


class WeeklyMenuItem(Base):
    __tablename__ = "weekly_menu_items"

    id = Column(Integer, primary_key=True, index=True)
    menu_id = Column(Integer, ForeignKey("weekly_menus.id"), nullable=False, index=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False, index=True)
    position = Column(Integer, nullable=False)  # 1-7, day of week

    # Relationships
    menu = relationship("WeeklyMenu", back_populates="items")
    recipe = relationship("Recipe", back_populates="menu_items")

    # Unique constraint: one recipe per position per menu
    __table_args__ = (UniqueConstraint("menu_id", "position", name="unique_menu_position"),)

    def __repr__(self):
        return f"WeeklyMenuItem(menu_id={self.menu_id}, position={self.position}, recipe_id={self.recipe_id})"


class ExternalIngredient(Base):
    __tablename__ = "external_ingredients"

    id = Column(Integer, primary_key=True, index=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False, index=True)
    ingredient_name = Column(String, nullable=False)

    # Relationship
    recipe = relationship("Recipe", back_populates="external_ingredients")

    def __repr__(self):
        return f"ExternalIngredient(recipe_id={self.recipe_id}, ingredient='{self.ingredient_name}')"
