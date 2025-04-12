from django.db import models
from core.models import User, Lead, Quote

class Event(models.Model):
    event_id = models.IntegerField(primary_key=True)
    lead = models.ForeignKey(Lead, related_name='marketing', db_column='lead_id', on_delete=models.CASCADE)
    street_address = models.CharField(max_length=255, null=True)
    city = models.CharField(max_length=100, null=True)
    zip_code = models.CharField(max_length=20, null=True)
    start_time = models.DateTimeField(null=True)
    end_time = models.DateTimeField(null=True)
    date_created = models.DateTimeField()
    date_paid = models.DateTimeField()
    amount = models.FloatField()
    tip = models.FloatField(null=True)
    guests = models.IntegerField()

    class Meta:
        db_table = 'event'

class Cocktail(models.Model):
    cocktail_id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=255)

    class Meta:
        db_table = 'cocktail'

class EventCocktail(models.Model):
    event_cocktail_id = models.IntegerField(primary_key=True)
    cocktail = models.ForeignKey(Cocktail, related_name='marketing', db_column='cocktail_id', on_delete=models.CASCADE)
    event = models.ForeignKey(Event, related_name='marketing', db_column='event_id', on_delete=models.CASCADE)

    class Meta:
        db_table = 'event_cocktail'

class Ingredient(models.Model):
    ingredient_id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=50)

    class Meta:
        db_table = 'ingredient'

class Unit(models.Model):
    unit_id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=50)
    abbreviation = models.CharField(max_length=20)

    class Meta:
        db_table = 'unit'

class CocktailIngredient(models.Model):
    cocktail = models.ForeignKey(Cocktail, related_name='cocktail', db_column='cocktail_id', on_delete=models.CASCADE)
    ingredient = models.ForeignKey(Ingredient, related_name='ingredient', db_column='ingredient_id', on_delete=models.SET_NULL)
    unit = models.ForeignKey(Unit, related_name='unit', db_column='unit_id', on_delete=models.SET_NULL)
    amount = models.FloatField()

    class Meta:
        db_table = 'cocktail_ingredient'
        unique_together = ('cocktail_id', 'ingredient_id', 'unit_id')

class EventRole(models.Model):
    event_role_id = models.IntegerField(primary_key=True)
    role = models.CharField(max_length=100)

    class Meta:
        db_table = 'event_role'

class EventStaff(models.Model):
    event_staff_id = models.IntegerField(primary_key=True)
    user = models.ForeignKey(User, related_name='user', db_column='user_id', on_delete=models.SET_NULL)
    event = models.ForeignKey(Event, related_name='event', db_column='event_id', on_delete=models.SET_NULL)
    event_role = models.ForeignKey(EventRole, related_name='event_role', db_column='event_role_id', on_delete=models.SET_NULL)
    hourly_rate = models.FloatField()
    
    class Meta:
        db_table = 'event_staff'
