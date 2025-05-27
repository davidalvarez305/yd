from django.db import migrations

def populate_unit_conversions(apps, schema_editor):
    Unit = apps.get_model("core", "Unit")
    UnitConversion = apps.get_model("core", "UnitConversion")

    conversions = [
        ("oz", "ml", 29.5735),
        ("cup", "ml", 236.588),
        ("pint", "ml", 473.176),
        ("quart", "ml", 946.353),
        ("gallon", "l", 3.78541),
        ("tsp", "ml", 4.92892),
        ("tbsp", "ml", 14.7868),
        ("shot", "ml", 44.3603),
        ("jigger", "ml", 44.3603),
        ("pony", "ml", 29.5735),
        ("dash", "ml", 0.92),
        ("splash", "ml", 3.7),
        ("drop", "ml", 0.05),
    ]

    for from_abbr, to_abbr, multiplier in conversions:
        from_unit = Unit.objects.get(abbreviation=from_abbr)
        to_unit = Unit.objects.get(abbreviation=to_abbr)

        # Forward conversion
        UnitConversion.objects.update_or_create(
            from_=from_unit,
            to=to_unit,
            defaults={'multiplier': multiplier}
        )

        # Reverse conversion
        reverse_multiplier = round(1 / multiplier, 6)
        UnitConversion.objects.update_or_create(
            from_=to_unit,
            to=from_unit,
            defaults={'multiplier': reverse_multiplier}
        )

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0012_conversion_units'),
    ]

    operations = [
        migrations.RunPython(populate_unit_conversions),
    ]
