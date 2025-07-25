# Generated by Django 5.1.7 on 2025-07-08 03:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0049_googlereview_should_show'),
    ]

    operations = [
        migrations.AlterField(
            model_name='servicetype',
            name='type',
            field=models.CharField(choices=[('service', 'Service'), ('rental', 'Rental'), ('food', 'Food'), ('add_on', 'Add On'), ('entertainment', 'Entertainment'), ('extend', 'Extend')], max_length=100, unique=True),
        ),
        migrations.AlterField(
            model_name='unittype',
            name='type',
            field=models.CharField(choices=[('per_person', 'Per Person'), ('hourly', 'Hourly'), ('fixed', 'Fixed')], max_length=100, unique=True),
        ),
    ]
