from datetime import datetime, timedelta
import math

from django.forms import ValidationError
from django.utils import timezone
from core.models import CocktailIngredient, Invoice, InvoiceType, InvoiceTypeEnum, Quote, QuoteService, Service, StoreItem, UnitConversion
from core.logger import logger

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

BASELINE_HOURS = 4.00
def calculate_quote_service_values(guests, hours, suggested_price, unit_type, service_type, guest_ratio):
    if unit_type == 'Per Person':
        units = guests
        price = suggested_price

        if service_type == "Add On":
            price *= (hours / BASELINE_HOURS)

        return {'units': units, 'price': price}

    elif unit_type == 'Hourly':
        units = (math.ceil(guests / guest_ratio) * hours) if guest_ratio else hours
        price = suggested_price
        return {'units': units, 'price': price}
    
    elif guest_ratio and 'Rental' in service_type:
        units = math.ceil(guests / guest_ratio)
        price = suggested_price
        return {'units': units, 'price': price}

    else:
        return {}

def update_quote_invoices(quote: Quote):
    try:
        """Updates invoice amounts when a quote or its services change."""
        amount_due = quote.amount()
        if quote.is_deposit_paid():
            remaining_invoice = quote.invoices.filter(invoice_type__type=InvoiceTypeEnum.REMAINING).first()
            if not remaining_invoice:
                raise Exception('No remaining invoice found.')
            remaining_invoice.amount = amount_due - quote.get_deposit_paid_amount()
            remaining_invoice.save()
        else:
            for invoice in quote.invoices.all():
                invoice.amount = amount_due * invoice.invoice_type.amount_percentage
                invoice.save()
    except Exception as e:
        logger.exception(str(e))
        raise Exception('Error updating quote services.')

def create_extension_invoice(quote_service: QuoteService):
    try:
        amount = quote_service.units * quote_service.price_per_unit
        extension_invoice = quote_service.quote.invoices.filter(invoice_type__type=InvoiceTypeEnum.EXTEND.value).first()
        if extension_invoice:
            extension_invoice += amount
            extension_invoice.save()
            return
        
        invoice_type = InvoiceType.objects.get(type=InvoiceTypeEnum.EXTEND.value)
        invoice = Invoice(
            quote=quote_service.quote,
            invoice_type=invoice_type,
            amount=amount,
            due_date=timezone.now() + timedelta(hours=24),
        )
        invoice.save()
    except Exception as e:
        logger.exception(str(e))
        raise Exception('Failed to create extension invoice.')

def create_quote_due_date(event_date):
    event_date_midnight = datetime.combine(event_date, datetime.min.time())

    due_datetime = event_date_midnight - timedelta(hours=48)

    due_datetime = timezone.make_aware(due_datetime)

    if due_datetime <= timezone.now():
        return timezone.now()

    return due_datetime
