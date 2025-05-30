import math

from django.forms import ValidationError
from core.models import CocktailIngredient, StoreItem, UnitConversion

def convert_to_item_quantity(cocktail_ingredient: CocktailIngredient, store_item: StoreItem, quantity: float):
    if not cocktail_ingredient.unit or not store_item.unit:
        raise ValidationError('Missing unit in either cocktail ingredient or store item.')
    
    conversion_multiplier = 1.0
    conversion = None
    is_conversion_the_same = cocktail_ingredient.unit.pk == store_item.unit.pk

    if not is_conversion_the_same:
        conversion = UnitConversion.objects.filter(from_unit=cocktail_ingredient.unit, to_unit=store_item.unit).first()
    
    if not conversion and not is_conversion_the_same:
        raise ValidationError(f'Unit conversion not found: {cocktail_ingredient.unit} to {store_item.unit}')
    
    if conversion:
        conversion_multiplier = conversion.multiplier

    total = quantity * conversion_multiplier

    return round_up_to_nearest(total, store_item.product_quantity)

def round_up_to_nearest(quantity, bottle_size):
    return math.ceil(quantity / bottle_size)