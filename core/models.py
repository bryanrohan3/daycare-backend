from django.db import models
from django.contrib.auth.models import User, AbstractUser
from rest_framework.authtoken.models import Token
from .utils.pet_types import PET_TYPES
from django.core.exceptions import ValidationError
from django.utils.crypto import get_random_string


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
    is_active = models.BooleanField(default=True)
    capacity = models.PositiveIntegerField(default=0) 
    pet_types = models.JSONField(default=list)
    # Pet Types -> Dog, Cat, Bird, Fish, Reptile, etc.

    def get_pet_types_display(self):
        # Returns the display names of the pet types
        return [PET_TYPES[pet_type_id] for pet_type_id in self.pet_types]


class OpeningHours(models.Model):
    DAYS = [
        (1, 'Monday'),
        (2, 'Tuesday'),
        (3, 'Wednesday'),
        (4, 'Thursday'),
        (5, 'Friday'),
        (6, 'Saturday'),
        (7, 'Sunday'),
    ]

    daycare = models.ForeignKey(Daycare, related_name='opening_hours', on_delete=models.CASCADE)
    day = models.PositiveSmallIntegerField(choices=DAYS)
    from_hour = models.TimeField(blank=True, null=True)
    to_hour = models.TimeField(blank=True, null=True)
    closed = models.BooleanField(default=False)
    capacity = models.PositiveIntegerField(default=0)

    def clean(self):
        if self.closed:
            if self.from_hour or self.to_hour:
                raise ValidationError("If the daycare is closed, opening and closing hours should not be set.")
        elif not self.from_hour or not self.to_hour:
            raise ValidationError("If the daycare is not closed, both opening and closing hours must be set.")
        elif self.from_hour >= self.to_hour:
            raise ValidationError("From time must be before To time")

    def __str__(self):
        if self.closed:
            return f"{self.get_day_display()}: Closed"
        return f"{self.get_day_display()}: {self.from_hour} - {self.to_hour}"
    

class Product(models.Model):
    """
    Daycare can have many Products, One Product can have one Daycare
    """
    daycare = models.ForeignKey(Daycare, related_name='products', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=5, decimal_places=2)
    capacity = models.PositiveIntegerField(null=True, blank=True)  # Optional capacity
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} - {self.daycare.daycare_name}"


class Roster(models.Model):
    staff = models.ForeignKey(StaffProfile, related_name='roster', on_delete=models.CASCADE) 
    daycare = models.ForeignKey(Daycare, related_name='roster', on_delete=models.CASCADE)
    start_shift = models.DateTimeField()
    end_shift = models.DateTimeField()
    shift_day = models.DateField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.staff.user.get_full_name()} - {self.daycare.daycare_name} - {self.shift_day}"


# Employees set their unavailabilities e.g Once off date or Monday every week etc
class StaffUnavailability(models.Model):
    DAYS = (
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    )

    staff = models.ForeignKey(StaffProfile, related_name='unavailability_days', on_delete=models.CASCADE) # get staff profile
    day_of_week = models.PositiveIntegerField(choices=DAYS, null=True, blank=True)
    date = models.DateField(null=True, blank=True)
    is_recurring = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        if self.is_recurring:
            return f"{self.get_day_of_week_display()} (Recurring)"
        else:
            return f"{self.date} (One-off)"


class Pet(models.Model):
    pet_name = models.CharField(max_length=25)
    # pet_type = ...
    pet_types = models.JSONField(default=list)
    pet_bio = models.TextField(blank=True)
    # photo = ? might make a seperate photo model since we might need to make a class Photo model incase we reuse it in other instances?
    customers = models.ManyToManyField(CustomerProfile, related_name='pets')
    is_public = models.BooleanField(default=True) # Public or Private
    is_active = models.BooleanField(default=True)
    invite_token = models.CharField(max_length=255, blank=True, null=True)

    def generate_invite_token(self):
        self.invite_token = get_random_string(50)
        self.save()

    def get_pet_types_display(self):
        """Returns the display names of the pet types."""
        # Ensure pet_types is a list, if not wrap it in a list
        if isinstance(self.pet_types, int):
            return [PET_TYPES[self.pet_types]]
        return [PET_TYPES[pet_type_id] for pet_type_id in self.pet_types if pet_type_id in PET_TYPES]

    def __str__(self):
        return self.pet_name


class PetNote(models.Model):
    pet = models.ForeignKey(Pet, related_name='notes', on_delete=models.CASCADE) # e.g pet/1/
    employee = models.ForeignKey(StaffProfile, related_name='pet_notes', on_delete=models.CASCADE) # e.g staff-profile/1
    note = models.TextField() # Maybe a max char count? not really needed though
    is_private = models.BooleanField(default=False)  # True if the note is private -> private for employees only

    def __str__(self):
        return f"Note for {self.pet.name} by {self.employee.user.get_full_name()}"

class Booking(models.Model):
    class Status(models.TextChoices):
        ACCEPTED = 'accepted', 'Accepted'
        WAITLISTED = 'waitlisted', 'Waitlisted'
        REJECTED = 'rejected', 'Rejected'

    customer = models.ForeignKey(CustomerProfile, on_delete=models.CASCADE)
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE)
    daycare = models.ForeignKey(Daycare, on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(max_length=50, choices=Status.choices, default=Status.ACCEPTED)
    is_active = models.BooleanField(default=True)
    checked_in = models.BooleanField(default=False)
    recurrence = models.BooleanField(default=False)  # Books 4 weeks in advance if true
    products = models.ManyToManyField(Product, related_name='bookings')
    is_waitlist = models.BooleanField(default=False)  
    waitlist_accepted = models.BooleanField(default=False)

    def __str__(self):
        return f"Booking({self.customer}, {self.pet}, {self.daycare}, {self.start_time}, {self.end_time})"

    @property
    def dynamic_status(self):
        if self.is_waitlist:
            return self.Status.WAITLISTED
        return self.Status.ACCEPTED if not self.waitlist_accepted else self.Status.REJECTED

    

class BlacklistedPet(models.Model):
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE)
    daycare = models.ForeignKey(Daycare, on_delete=models.CASCADE)
    reason = models.TextField(blank=True, null=True)
    date_blacklisted = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.pet} is blacklisted from {self.daycare}"
    

class Waitlist(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE)
    customer_notified = models.BooleanField(default=False)
    waitlisted_at = models.DateTimeField(auto_now_add=True)
    customer_accepted = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Waitlist({self.booking}, notified: {self.customer_notified})"
    

# class Post(models.Model):
#     class Status(models.TextChoices):
#         PUBLIC = 'public', 'Public'
#         PRIVATE = 'private', 'Private'
#         PROTECTED = 'protected', 'Protected'
#     user = models.ForeignKey(StaffProfile, on_delete=models.CASCADE)
#     daycare = models.ForeignKey(Daycare, on_delete=models.CASCADE)
#     # pets -> post tags Pets [1,5]
#     caption = models.CharField(max_length=250)
#     date_time_created = models.DateTimeField(auto_now_add=True)
#     is_active = models.BooleanField(default=True)
#     status = models.CharField(max_length=50, choices=Status.choices)
#     tagged_pets = models.ManyToManyField(Pet, related_name='pets')

#     # Check on Status
#     # psuedo
#     # if customer.booking__in_daycare:
#         # return Protected
#     # elif pet.is_public=False:
#     #   return Private 
#     # else:
#     #   return Public


#     def __str__(self):
#         return f'Post created by {self.user} at {self.date_time_created}'
    

# class Like(models.Model):
#     user = models.ForeignKey(User, on_delete=models.CASCADE)
#     post = models.ForeignKey(Post, on_delete=models.CASCADE) # User since both Staff and Customer can like posts

#     def _str__(self):
#         return f'{self.user.username} liked {self.post}'


# class Comment(models.Model):
#     user = models.ForeignKey(User, on_delete=models.CASCADE)
#     post = models.ForeignKey(Post, on_delete=models.CASCADE)
#     text = models.TextField(max_length=200)
#     is_active = models.BooleanField(default=True)
#     date_time_created = models.DateTimeField(auto_now_add=True)

#     def __str__(self):  
#         return f'Comment by {self.user.username} on {self.post}'
    