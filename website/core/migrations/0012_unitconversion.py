import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0011_ingredientcategory_remove_ingredient_category_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='UnitConversion',
            fields=[
                ('unit_conversion_id', models.AutoField(primary_key=True, serialize=False)),
                ('multiplier', models.FloatField()),
                ('from_', models.ForeignKey(
                    db_column='from',
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='unit_conversions_from',
                    to='core.unit'
                )),
                ('to', models.ForeignKey(
                    db_column='to',
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='unit_conversions_to',
                    to='core.unit'
                )),
            ],
            options={
                'db_table': 'unit_conversion',
                'unique_together': {('from_', 'to')},
            },
        ),
        migrations.CreateModel(
            name='Store',
            fields=[
                ('store_id', models.AutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=50)),
            ],
            options={
                'db_table': 'store',
            },
        ),
    ]
