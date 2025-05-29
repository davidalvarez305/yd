import math

from django.forms import ValidationError
from core.models import CocktailIngredient, StoreItem, UnitConversion

def convert_to_item_quantity(cocktail_ingredient: CocktailIngredient, store_item: StoreItem):
    if not cocktail_ingredient.unit or not store_item.unit:
        raise ValidationError('Missing unit in either cocktail ingredient or store item.')
    
    conversion = UnitConversion.objects.filter(from_unit=cocktail_ingredient.unit, to_unit=store_item.unit).first()
    
    if not conversion:
        raise ValidationError('Unit conversion not found.')
    
    total = cocktail_ingredient.amount * conversion.multiplier

    return round_up_to_nearest(total, store_item.product_quantity)

def round_up_to_nearest(quantity, step):
    return math.ceil(quantity / step) * step