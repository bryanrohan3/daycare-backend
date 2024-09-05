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

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.user.username}) - Role: {self.get_role_display()}"

    def get_role_display(self):
        return dict(self.ROLE_CHOICES)[self.role]
    

class CustomerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    # pets -> A Customer can have Many Pets and a Pet can have Many Customers
    # Customer has Pet A, Pet B -> Pet A belongs to Customer A and Customer B, Pet B belongs to Customer A
    phone = models.CharField(max_length=15)  # Format: +61-123-234-234
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.user.username}) - Phone: {self.phone}"
