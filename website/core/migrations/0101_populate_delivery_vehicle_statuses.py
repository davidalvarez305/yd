from django.db import migrations

def create_vehicle_statuses(apps, schema_editor):
    DeliveryVehicleStatus = apps.get_model("core", "DeliveryVehicleStatus")

    statuses = [
        "Active",
        "Assigned",
        "Ready For Dispatch",
        "On The Road",
        "Inactive",
    ]

    for status in statuses:
        DeliveryVehicleStatus.objects.get_or_create(status=status)

class Migration(migrations.Migration):

    dependencies = [
        ("core", "0100_deliveryvehicle_deliveryvehiclestatus_and_more"),
    ]

    operations = [
        migrations.RunPython(
            create_vehicle_statuses,
        ),
    ]