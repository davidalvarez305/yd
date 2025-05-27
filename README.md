# On Windows (Command Prompt)
env\Scripts\activate

# On Windows (PowerShell)
Set-ExecutionPolicy Unrestricted -Scope Process

env\Scripts\Activate.ps1

# On Unix
source env/bin/activate

# Windows PG
cd "Program Files\PostgreSQL\17\bin"

pg_ctl.exe -D "C:\Program Files\PostgreSQL\17\data" start

# Populating DB Sample

# Create Empty Migration File
```shell
python manage.py makemigrations core --empty --name populate_units
```

# Add Data
```python
from django.db import migrations

def populate_units(apps, schema_editor):
    Unit = apps.get_model("core", "Unit")
    units = [
        {"unit_id": 1, "name": "Ounce", "abbreviation": "oz"},
        {"unit_id": 2, "name": "Milliliter", "abbreviation": "ml"},
        {"unit_id": 3, "name": "Liter", "abbreviation": "l"},
        {"unit_id": 4, "name": "Teaspoon", "abbreviation": "tsp"},
        {"unit_id": 5, "name": "Tablespoon", "abbreviation": "tbsp"},
        {"unit_id": 6, "name": "Dash", "abbreviation": "dash"},
        {"unit_id": 7, "name": "Drop", "abbreviation": "drop"},
        {"unit_id": 8, "name": "Shot", "abbreviation": "shot"},
        {"unit_id": 9, "name": "Jigger", "abbreviation": "jigger"},
        {"unit_id": 10, "name": "Pony", "abbreviation": "pony"},
        {"unit_id": 11, "name": "Cup", "abbreviation": "cup"},
        {"unit_id": 12, "name": "Splash", "abbreviation": "splash"},
        {"unit_id": 13, "name": "Gram", "abbreviation": "g"},
        {"unit_id": 14, "name": "Kilogram", "abbreviation": "kg"},
        {"unit_id": 15, "name": "Pound", "abbreviation": "lb"},
        {"unit_id": 16, "name": "Piece", "abbreviation": "pc"},
        {"unit_id": 17, "name": "Cube", "abbreviation": "cube"},
        {"unit_id": 18, "name": "Leaf", "abbreviation": "leaf"},
        {"unit_id": 19, "name": "Clove", "abbreviation": "clove"},
        {"unit_id": 20, "name": "Egg", "abbreviation": "egg"},
        {"unit_id": 21, "name": "Slice", "abbreviation": "slice"},
        {"unit_id": 22, "name": "Wedge", "abbreviation": "wedge"},
        {"unit_id": 23, "name": "Twist", "abbreviation": "twist"},
        {"unit_id": 24, "name": "Stick", "abbreviation": "stick"},
        {"unit_id": 25, "name": "Part", "abbreviation": "part"},
        {"unit_id": 26, "name": "Top", "abbreviation": "top"},
        {"unit_id": 27, "name": "Rim", "abbreviation": "rim"},
    ]

    for unit in units:
        Unit.objects.update_or_create(unit_id=unit["unit_id"], defaults=unit)

class Migration(migrations.Migration):

    dependencies = [
        ("core", "XXXX_previous_migration_name"),
    ]

    operations = [
        migrations.RunPython(populate_units),
    ]
```

# Apply Migrations
```shell
python manage.py migrate core
```