from django.db import migrations


def populate_choice_tables(apps, schema_editor):
    BusinessSegment = apps.get_model('core', 'BusinessSegment')
    DriverStopStatus = apps.get_model('core', 'DriverStopStatus')
    ItemState = apps.get_model('core', 'ItemState')
    OrderStatus = apps.get_model('core', 'OrderStatus')
    OrderTask = apps.get_model('core', 'OrderTask')
    OrderTaskStatus = apps.get_model('core', 'OrderTaskStatus')

    # -------------------------
    # BusinessSegment
    # -------------------------
    for segment in [
        'Bartending',
        'Rentals',
    ]:
        BusinessSegment.objects.get_or_create(segment=segment)

    # -------------------------
    # DriverStopStatus
    # -------------------------
    for status in [
        'Allocated',
        'Out For Delivery',
        'Completed',
        'Delivery Failed',
    ]:
        DriverStopStatus.objects.get_or_create(status=status)

    # -------------------------
    # ItemState
    # -------------------------
    for state in [
        'Reserved',
        'Returned',
        'Purchased',
        'Sold',
        'Decommissioned',
    ]:
        ItemState.objects.get_or_create(state=state)

    # -------------------------
    # OrderStatus
    # -------------------------
    for status in [
        'Order Placed',
        'Order Cancelled',
        'Awaiting Preparation',
        'Ready for Dispatch',
        'Dispatched',
        'Finalized',
        'Delivery Failed',
        'Pending Review of Delivery',
        'Delivered',
        'Pending Pick Up',
        'Picked Up',
        'Customer Picked Up',
        'Pending Customer Return',
        'Customer Returned',
    ]:
        OrderStatus.objects.get_or_create(status=status)

    # -------------------------
    # OrderTask
    # -------------------------
    for task in ['Load Order Items', 'Unload Order Items']:
        OrderTask.objects.get_or_create(task=task)

    # -------------------------
    # OrderTaskStatus
    # -------------------------
    for status in [
        'Assigned',
        'In Progress',
        'Unable To Complete',
        'Completed',
    ]:
        OrderTaskStatus.objects.get_or_create(status=status)


def reverse_populate_choice_tables(apps, schema_editor):
    """
    Intentionally left empty.
    We never want to auto-delete production lookup data.
    """
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0091_address_businesssegment_driverstopstatus_and_more'),
    ]

    operations = [
        migrations.RunPython(
            populate_choice_tables,
            reverse_populate_choice_tables,
        ),
    ]