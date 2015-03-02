from django.contrib.auth.models import AbstractUser
from django.db import models
from decimal import Decimal
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import User, Group

'''Clase para las constructoras'''
class ConstructorCompany(models.Model):
    user = models.OneToOneField(User,null=True)
    nit = models.CharField(max_length=15)
    company_name = models.CharField(max_length=100)
    address = models.CharField(max_length=100)
    fixed_phone = models.PositiveIntegerField(validators=[MinValueValidator(0000000), MaxValueValidator(9999999)], null=True)
    fixed_phone_extension = models.PositiveIntegerField(validators=[MinValueValidator(00000), MaxValueValidator(99999)], null=True)
    mobile_number = models.CharField(max_length=15, null=True)
    email = models.EmailField(max_length=50, blank=False, unique=True)
    contact_name = models.CharField(max_length=100)

'''Clase para los inmuebles'''
class Property(models.Model):
    name = models.CharField(max_length=60)
    address = models.CharField(max_length=100, null=True)
    fixed_phone = models.CharField(max_length=15, null=True)
    plan = models.CharField(max_length=60, null=True)
    constructor_company = models.ForeignKey(ConstructorCompany, null=True)
	
'''Clase extendida de User, se usa para autenticacion, y relaciona las propiedades que un usuario tiene como propietario o residente'''
class UserProfile(models.Model):
    user = models.OneToOneField(User)
    mobile_number = models.CharField(max_length=15)
    properties_as_resident = models.ManyToManyField(Property, related_name="properties_as_resident")
    properties_as_owner = models.ManyToManyField(Property, related_name="properties_as_owner")

'''Clase para sensores y actuadores'''
class Sensor(models.Model):
    SENSOR_TYPES_CHOICES = (
    	('0', 'Sensor digital'),
    	('1', 'Sensor analogo'),
    	('2', 'Sensor PWM'),
    	('3', 'Actuador digital'),
    	('4', 'Actuador analogo'),
    	('5', 'Actuador PWM'),
    )
    SENSOR_STATUS_CHOICES = (
        ('0', 'Encendido'),
        ('1', 'Apagado'),
    )
    code = models.CharField(max_length=15)
    description = models.CharField(max_length=60)
    type = models.CharField(max_length=30, choices=SENSOR_TYPES_CHOICES)
    location_in_plan = models.CharField(max_length=20,null=True)
    color = models.CharField(max_length=20,null=True)
    status = models.CharField(max_length=10, choices=SENSOR_STATUS_CHOICES)

'''Clase para eventos'''
class Event(models.Model):
    EVENT_CHOICES = (
        ('0', 'Disparo de alarma'),
        ('1', 'Activar alarma'),
        ('3', 'Alerta en sensor'),
        ('2', 'Desactivar alarma'),
        ('4', 'Cambio actuador'),
    )
    date = models.DateTimeField()
    description = models.CharField(max_length=200)
    value = models.DecimalField(max_digits=10, decimal_places=2)
    type = models.CharField(max_length=30, choices=EVENT_CHOICES)
    property = models.ForeignKey(Property)
    sensor = models.ForeignKey(Sensor)