from django.db import models
from django.contrib.auth.models import User, AbstractUser
from rest_framework.authtoken.models import Token

# Create your models here.
class StaffProfile(models.Model):
    ROLE_CHOICES = (
        ('O', 'Owner'),
        ('E', 'Employee'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    phone = models.CharField(max_length=15)
    is_active = models.BooleanField(default=True)
    daycares = models.ManyToManyField('Daycare', blank=True)

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.user.username}) - Role: {self.get_role_display()}"

    def get_role_display(self):
        return dict(self.ROLE_CHOICES)[self.role]
    

class CustomerProfile(models.Model):
    """
    Customer Profile Can Only Be Created By Staff (Owner or Employee)
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    # pets -> A Customer can have Many Pets and a Pet can have Many Customers
    # Customer has Pet A, Pet B -> Pet A belongs to Customer A and Customer B, Pet B belongs to Customer A
    phone = models.CharField(max_length=15)  # Format: +61-123-234-234
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.user.username}) - Phone: {self.phone}"


# TODO:
# - Owner Creates Daycare ("O" not "E")
# - Daycare Details -> Name, Address, Phone, Email, Opening Hours, Pet Types, Capacitiy (hidden to public)
class Daycare(models.Model):
    AUSTRALIAN_STATES = [
        ('NSW', 'New South Wales'),
        ('VIC', 'Victoria'),
        ('QLD', 'Queensland'),
        ('SA', 'South Australia'),
        ('WA', 'Western Australia'),
        ('TAS', 'Tasmania'),
        ('NT', 'Northern Territory'),
        ('ACT', 'Australian Capital Territory'),
    ]

    daycare_name = models.CharField(max_length=100)
    street_address = models.CharField(max_length=100)
    suburb = models.CharField(max_length=100)
    state = models.CharField(max_length=3, choices=AUSTRALIAN_STATES)
    postcode = models.CharField(max_length=4)
    phone = models.CharField(max_length=15)
    email = models.EmailField()
    # is_active = models.BooleanField(default=True) -> add this in next migration to ensure daycare is active or not (soft delete)
    # capacity = models.IntegerField() -> this will change though from Monday to Sunday?
    # Pet Types -> Dog, Cat, Bird, Fish, Reptile, etc.
    # Opening Hours -> Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday (Timings?)
