from datetime import datetime, timedelta
import math
import io
import uuid

# from weasyprint import HTML

from django.db.models import F, Sum, FloatField, ExpressionWrapper
from django.template.loader import render_to_string
from django.forms import ValidationError
from django.utils import timezone
from django.core.files.base import ContentFile

from core.models import CocktailIngredient, Event, EventDocument, Invoice, InvoiceType, InvoiceTypeEnum, LandingPage, Quote, QuoteService, Service, StoreItem, UnitConversion
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
HOLIDAY_MARKUPS = {
    (11, 27),
    (12, 24),
    (12, 31),
}

def calculate_quote_service_values(
    adults, minors, hours, suggested_price,
    unit_type, service_type, guest_ratio, date
):
    minors = minors or 0
    adults = adults or 0

    guests = adults + minors

    def apply_holiday_markup(price):
        if (date.month, date.day) in HOLIDAY_MARKUPS:
            return price * 1.50
        return price

    def apply_large_group_discount(price):
        if adults >= 200:
            return price * 0.50
        elif adults >= 100:
            return price * 0.60
        elif adults >= 80:
            return price * 0.70
        elif adults >= 60:
            return price * 0.85
        elif adults >= 40:
            return price * 0.90
        return price

    if unit_type == 'Per Person':
        units = guests if service_type != 'Alcohol' else adults
        price = suggested_price

        if service_type in {"Add On", "Alcohol"}:
            extra_hours = max(0, hours - BASELINE_HOURS)
            price *= (1 + 0.075 * extra_hours)

        price = apply_holiday_markup(price)

        total = price

        if service_type != 'Extra':
            total = apply_large_group_discount(price)

        return {'units': units, 'price': total}

    elif unit_type == 'Ratio' and service_type == 'Hourly Service':
        units = (math.ceil(adults / guest_ratio) * hours) if guest_ratio else hours
        price = apply_holiday_markup(suggested_price)

        return {'units': units, 'price': price}

    elif unit_type == 'Hourly':
        units = (math.ceil(adults / guest_ratio) * hours) if guest_ratio else hours
        price = apply_holiday_markup(suggested_price)

        return {'units': units, 'price': price}

    elif guest_ratio and service_type in {'Bar Rental', 'Cooler Rental'}:
        units = math.ceil(adults / guest_ratio)
        price = apply_holiday_markup(suggested_price)

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

def generate_event_pdf(event: Event) -> EventDocument:
    quote = event.quotes.first()
    if not quote:
        raise ValueError("No quote found for event")

    pages = [
        render_to_string('crm/external_quote_view.html', {'quote': quote}),
        render_to_string('crm/event_external_detail.html', {'event': event}),
    ]

    html_string = "<div style='page-break-after: always'></div>".join(pages)

    pdf_buffer = io.BytesIO()
    # HTML(string=html_string).write_pdf(pdf_buffer)
    pdf_buffer.seek(0)

    filename = f"{uuid.uuid4()}.pdf"

    document = EventDocument.objects.create(
        event=event,
        document=ContentFile(pdf_buffer.read(), name=filename)
    )

    return document

def quote_revenue(qs):
    return (
        qs.annotate(
            line_total=ExpressionWrapper(
                F('quote_services__units') * F('quote_services__price_per_unit'),
                output_field=FloatField(),
            )
        )
        .aggregate(total=Sum('line_total'))['total'] or 0
    )