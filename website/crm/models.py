from django.db import models
from core.models import Cocktail

class Ingredient(models.Model):
    ingredient_id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=50)

    class Meta:
        db_table = 'ingredient'

class Unit(models.Model):
    unit_id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=50)
    abbreviation = models.CharField(max_length=20)

    class Meta:
        db_table = 'unit'

class CocktailIngredient(models.Model):
    cocktail = models.ForeignKey(
        Cocktail,
        related_name='ingredients',
        db_column='cocktail_id',
        on_delete=models.CASCADE
    )
    ingredient = models.ForeignKey(
        Ingredient,
        related_name='used_in_cocktails',
        db_column='ingredient_id',
        null=True,
        on_delete=models.SET_NULL
    )
    unit = models.ForeignKey(
        Unit,
        related_name='used_in_cocktails',
        db_column='unit_id',
        null=True,
        on_delete=models.SET_NULL
    )
    amount = models.FloatField()

    class Meta:
        db_table = 'cocktail_ingredient'
        unique_together = ('cocktail', 'ingredient', 'unit')
