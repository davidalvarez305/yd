import math

from django.forms import ValidationError
from core.models import CocktailIngredient, StoreItem, UnitConversion

def round_up_to_nearest(quantity: float, step: float) -> int:
    if step <= 0:
        raise ValueError("Step must be greater than zero.")
    return math.ceil(quantity / step)

def convert_to_item_quantity(cocktail_ingredient: CocktailIngredient, store_item: StoreItem, quantity: float) -> int:
    if not cocktail_ingredient.unit or not store_item.unit:
        raise ValidationError("Missing unit in either cocktail ingredient or store item.")
    
    if not store_item.product_quantity:
        raise ValidationError("Store item is missing a defined product quantity.")

    if cocktail_ingredient.unit.pk == store_item.unit.pk:
        conversion_multiplier = 1.0
    else:
        conversion = UnitConversion.objects.filter(from_unit=cocktail_ingredient.unit, to_unit=store_item.unit).first()
        
        if not conversion:
            raise ValidationError(f"Unit conversion not found: {cocktail_ingredient.unit} to {store_item.unit}")
        
        conversion_multiplier = conversion.multiplier

    total = quantity * conversion_multiplier

    return round_up_to_nearest(total, store_item.product_quantity)