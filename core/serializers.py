from rest_framework import serializers
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from .models import *
from django.utils.dateparse import parse_datetime
from django.utils import timezone


class UserSerializer(serializers.ModelSerializer):
    token = serializers.SerializerMethodField()
    account_type = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'password', 'token', 'is_active', 'account_type']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user

    def get_token(self, obj):
        token, created = Token.objects.get_or_create(user=obj)
        return token.key
    
    def get_account_type(self, user):
        if hasattr(user, 'staffprofile'):
            return 'staff'
        elif hasattr(user, 'customerprofile'):
            return 'customer'
        return 'unknown'

class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()


class BasicStaffUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['first_name', 'last_name']


class BasicStaffProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = StaffProfile
        fields = ['id','user', 'role', 'phone', 'is_active']


class StaffProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    daycares = serializers.PrimaryKeyRelatedField(
        queryset=Daycare.objects.all(),
        many=True,
        required=False
    )
    daycares_names = serializers.SerializerMethodField()

    class Meta:
        model = StaffProfile
        fields = ['id', 'user', 'role', 'phone', 'is_active', 'daycares', 'daycares_names']

    def get_daycares_names(self, obj):
        # Ensure obj.daycares is a queryset
        return BasicDaycareSerializerStaff(obj.daycares.all(), many=True).data

    def create(self, validated_data):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("Authentication credentials were not provided.")

        creator_profile = StaffProfile.objects.get(user=request.user)
        if creator_profile.role != 'O':
            raise serializers.ValidationError("Only Owners can create new profiles.")

        user_data = validated_data.pop('user')
        daycares = validated_data.pop('daycares', [])

        # Validate daycares
        if daycares:
            # Convert daycares to a list of IDs for validation
            daycare_ids = [daycare.id for daycare in daycares] if isinstance(daycares[0], Daycare) else daycares
            creator_daycare_ids = creator_profile.daycares.values_list('id', flat=True)
            if not all(daycare_id in creator_daycare_ids for daycare_id in daycare_ids):
                raise serializers.ValidationError("You can only assign staff to daycares you are associated with.")

        # Create or get the user instance
        user_serializer = UserSerializer(data=user_data)
        user_serializer.is_valid(raise_exception=True)
        user = user_serializer.save()

        staff_profile = StaffProfile.objects.create(user=user, **validated_data)
        staff_profile.daycares.set(daycare_ids)  # Set daycares for the new staff profile

        return staff_profile

class BasicDaycareSerializerStaff(serializers.ModelSerializer):
    class Meta:
        model = Daycare
        fields = ['id', 'daycare_name']

class BasicUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['first_name', 'last_name']

class BasicRosterStaffProfileSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source='user.first_name')
    last_name = serializers.CharField(source='user.last_name')

    class Meta:
        model = StaffProfile
        fields = ['id','first_name', 'last_name', 'role']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        return representation

class BasicPetSerializer(serializers.ModelSerializer):
    pet_types_display = serializers.SerializerMethodField()
    customers = serializers.SerializerMethodField() 

    class Meta:
        model = Pet
        fields = ['id', 'pet_name', 'pet_bio', 'is_public', 'is_active', 'pet_types_display', 'customers']

    def get_pet_types_display(self, obj):
        return obj.get_pet_types_display()  

    def get_customers(self, obj):
        return CustomerBasicProfileSerializer(obj.customers.all(), many=True).data 
    

class BasicPetNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pet
        fields = ['id', 'pet_name']


class CustomerProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    pets = serializers.SerializerMethodField()
    # Serializer Classes here need to be added

    class Meta:
        model = CustomerProfile
        fields = ['id', 'user', 'phone', 'pets', 'is_active']

    def get_pets(self, obj):
        return BasicPetSerializer(obj.pets.all(), many=True).data 

    def create(self, validated_data):
        user_data = validated_data.pop('user')
        user = UserSerializer().create(user_data)
        customer_profile = CustomerProfile.objects.create(user=user, **validated_data)
        
        return customer_profile


class CustomerBasicProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField() 
    class Meta:
        model = CustomerProfile
        fields = ['id', 'user', 'full_name'] 

    def get_full_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}" 
    

class OpeningHoursSerializer(serializers.ModelSerializer):
    day_name = serializers.SerializerMethodField()

    class Meta:
        model = OpeningHours
        fields = ['day', 'day_name', 'from_hour', 'to_hour', 'closed', 'capacity']

    def get_day_name(self, obj):
        return obj.get_day_display()


class ProductSerializer(serializers.ModelSerializer):
    daycare_name = serializers.ReadOnlyField(source='daycare.daycare_name')

    class Meta:
        model = Product
        fields = ['id', 'name', 'description', 'price', 'capacity', 'daycare', 'daycare_name', 'is_active']


class DaycareSerializer(serializers.ModelSerializer):
    staff = serializers.SerializerMethodField()
    opening_hours = OpeningHoursSerializer(many=True)
    products = ProductSerializer(many=True, read_only=True)
    pet_types_display = serializers.SerializerMethodField()

    class Meta:
        model = Daycare
        fields = ['id', 'daycare_name', 'street_address', 'suburb', 'state', 'postcode', 'phone', 'email', 'staff', 'is_active', 'capacity', 'opening_hours', 'products', 'pet_types' ,'pet_types_display']

    def get_pet_types_display(self, obj):
        return obj.get_pet_types_display()

    def get_staff(self, obj):
        request = self.context.get('request')
        if not request:
            return []
        role = request.query_params.get('role')
        if role and role in ['O', 'E']:
            staff = StaffProfile.objects.filter(daycares=obj, role=role)
        else:
            staff = StaffProfile.objects.filter(daycares=obj)
        return BasicStaffProfileSerializer(staff, many=True).data

    def create(self, validated_data):
        opening_hours_data = validated_data.pop('opening_hours', [])
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("Authentication credentials were not provided.")
        try:
            creator_profile = StaffProfile.objects.get(user=request.user)
            if creator_profile.role != 'O':
                raise serializers.ValidationError("Only Owners can create Daycare entries.")
        except StaffProfile.DoesNotExist:
            raise serializers.ValidationError("Only Owners can create Daycare entries.")
        daycare = Daycare.objects.create(**validated_data)
        creator_profile.daycares.add(daycare)
        for oh_data in opening_hours_data:
            OpeningHours.objects.create(daycare=daycare, **oh_data)
        return daycare

    def update(self, instance, validated_data):
        opening_hours_data = validated_data.pop('opening_hours', [])

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if opening_hours_data:
            # Remove existing opening hours if any
            instance.opening_hours.all().delete()
            # Add new opening hours
            for oh_data in opening_hours_data:
                OpeningHours.objects.create(daycare=instance, **oh_data)

        return instance


class CustomerDaycareSerializer(serializers.ModelSerializer):
    opening_hours = OpeningHoursSerializer(many=True)

    class Meta:
        model = Daycare
        fields = ['id', 'daycare_name', 'street_address', 'suburb', 'state', 'postcode', 'phone', 'email', 'opening_hours']


class RosterSerializer(serializers.ModelSerializer):
    staff_id = serializers.PrimaryKeyRelatedField(queryset=StaffProfile.objects.all(), source='staff', write_only=True)
    staff = BasicRosterStaffProfileSerializer(read_only=True)
    daycare = serializers.PrimaryKeyRelatedField(queryset=Daycare.objects.all())

    class Meta:
        model = Roster
        fields = ['id', 'staff_id', 'staff', 'daycare', 'start_shift', 'end_shift', 'shift_day', 'is_active']

    def validate(self, data):
        self.validate_staff_daycare_association(data)
        self.check_overlapping_shifts(data)
        self.check_unavailability(data)
        return data

    def validate_staff_daycare_association(self, data):
        staff = data.get('staff')
        daycare = data.get('daycare')
        
        if not staff.daycares.filter(id=daycare.id).exists():
            raise serializers.ValidationError("Staff does not work in the specified daycare.")

    def check_overlapping_shifts(self, data):
        staff = data.get('staff')
        start_shift = data.get('start_shift')
        end_shift = data.get('end_shift')
        shift_day = data.get('shift_day')

        # Exclude the current shift being updated
        current_shift_id = self.instance.id if self.instance else None
        # Get all shifts for the staff on the same shift day
        existing_shifts = Roster.objects.filter(staff=staff, shift_day=shift_day).exclude(id=current_shift_id)

        for shift in existing_shifts:
            existing_start = shift.start_shift
            existing_end = shift.end_shift
            if (start_shift < existing_end and end_shift > existing_start):
                raise serializers.ValidationError("Staff already has a shift that overlaps with another shift on the same day.")

    def check_unavailability(self, data):
        staff = data.get('staff')
        start_shift = data.get('start_shift')
        shift_day_of_week = start_shift.weekday()

        # Check recurring unavailability
        recurring_unavailability = staff.unavailability_days.filter(is_recurring=True)
        for unavailability in recurring_unavailability:
            if unavailability.day_of_week == shift_day_of_week:
                raise serializers.ValidationError(f"{staff} is unavailable on {unavailability.get_day_of_week_display()} (Recurring).")

        # Check one-off unavailability
        one_off_unavailability = staff.unavailability_days.filter(is_recurring=False)
        for unavailability in one_off_unavailability:
            if unavailability.date == start_shift.date():
                raise serializers.ValidationError(f"{staff} is unavailable on {unavailability.date} (One-off).")

    def create(self, validated_data):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("Authentication credentials were not provided.")

        # Fetch the staff profile of the currently authenticated user
        staff_profile = request.user.staffprofile

        # Ensure the staff profile is associated with the daycare
        daycare = validated_data['daycare']
        if not staff_profile.daycares.filter(id=daycare.id).exists():
            raise serializers.ValidationError("You cannot create a roster for a daycare you are not associated with.")

        return super().create(validated_data)


class StaffUnavailabilitySerializer(serializers.ModelSerializer):
    staff = BasicRosterStaffProfileSerializer(read_only=True)
    class Meta:
        model = StaffUnavailability
        fields = ['id', 'staff', 'day_of_week', 'date', 'is_recurring', 'is_active']
        read_only_fields = ['staff']

    def validate(self, data):
        if data.get('is_recurring') and data.get('day_of_week') is None:
            raise serializers.ValidationError("Recurring unavailability requires a 'day_of_week'.")
        if not data.get('is_recurring') and data.get('date') is None:
            raise serializers.ValidationError("Non-recurring unavailability requires a 'date'.")
        return data


class PetNameOnlySerializer(serializers.ModelSerializer):
    class Meta:
        model = Pet
        fields = ['id', 'pet_name', 'pet_bio', 'is_public', 'is_active']


class PetSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pet
        fields = ['id', 'pet_name']  # Only include pet ID and pet_name


class PetSerializer(serializers.ModelSerializer):
    pet_types_display = serializers.SerializerMethodField()
    customers = serializers.SerializerMethodField()

    class Meta:
        model = Pet
        fields = ['id', 'pet_name', 'pet_types', 'pet_bio', 'is_public', 'is_active', 'invite_token', 'pet_types_display', 'customers']
        extra_kwargs = {
            'is_active': {'default': True},
            'is_public': {'default': True},
        }

    def get_pet_types_display(self, obj):
        return obj.get_pet_types_display()

    def get_customers(self, obj):
        return [{
            'id': customer.id,
            'full_name': customer.user.get_full_name(),
            'phone': customer.phone,
            'email': customer.user.email
        } for customer in obj.customers.all()]

    def to_representation(self, instance):
        request = self.context.get('request', None)

        # If the pet is private and the user is not a customer, return limited information
        if not instance.is_public and request:
            user = request.user
            if not hasattr(user, 'customerprofile') or user.customerprofile not in instance.customers.all():
                # Use PetNameOnlySerializer to return just the pet name
                return PetNameOnlySerializer(instance).data

        # Otherwise, return the full representation
        return super().to_representation(instance)



class PetNoteSerializer(serializers.ModelSerializer):
    pet = serializers.PrimaryKeyRelatedField(queryset=Pet.objects.all())
    employee = serializers.PrimaryKeyRelatedField(queryset=StaffProfile.objects.all())

    class Meta:
        model = PetNote
        fields = ['id', 'pet', 'employee', 'note', 'is_private']

    def create(self, validated_data):
        return PetNote.objects.create(**validated_data)


class BookingSerializer(serializers.ModelSerializer):
    products = serializers.PrimaryKeyRelatedField(many=True, queryset=Product.objects.all(), required=False)
    customer_details = CustomerBasicProfileSerializer(source='customer', read_only=True)
    pet_details = PetSimpleSerializer(source='pet', read_only=True)

    class Meta:
        model = Booking
        fields = ['id', 'customer', 'pet', 'daycare', 'start_time', 'end_time', 'status', 'is_active', 'recurrence', 'products', 'customer_details', 'pet_details', 'checked_in', 'is_waitlist', 'waitlist_accepted']
        read_only_fields = ['status']

    def validate(self, attrs):
        request = self.context['request']
        user = request.user
        pet = attrs.get('pet')
        daycare = attrs.get('daycare')

        current_time = timezone.now()

        if hasattr(user, 'customerprofile'):
            attrs['customer'] = user.customerprofile
        else:
            attrs['customer'] = attrs.get('customer')

        # Check if the customer owns the pet
        if pet and attrs['customer'] and attrs['customer'] not in pet.customers.all():
            raise serializers.ValidationError({"pet": "This pet does not belong to the customer."})

        # Check if the staff user is associated with the daycare
        if hasattr(user, 'staffprofile') and daycare:
            if not user.staffprofile.daycares.filter(id=daycare.id).exists():
                raise serializers.ValidationError({"daycare": "You are not associated with this daycare."})

        blacklisted_pet = BlacklistedPet.objects.filter(pet=pet, daycare=daycare, is_active=True).first()
        if blacklisted_pet:
            raise serializers.ValidationError({"pet": "This pet is blacklisted from this daycare."})

        start_time = attrs.get('start_time')
        end_time = attrs.get('end_time')

        if not self.is_daycare_open(daycare, start_time):
            raise serializers.ValidationError({"start_time": "The daycare is closed on the selected day."})

        if not self.is_within_opening_hours(daycare, start_time, end_time):
            raise serializers.ValidationError({"start_time": "The booking times are outside of the daycare's opening hours."})

        if self.has_overlapping_bookings(pet, daycare, start_time, end_time):
            raise serializers.ValidationError({"start_time": "This pet already has a booking during the requested time."})

        # Check if the daycare has capacity
        if not self.has_capacity(daycare, start_time, end_time):
            attrs['is_waitlist'] = True  # Set waitlist flag
            self.add_warning("The daycare has reached its capacity for the selected time, your booking will be on the waitlist.")

        else:
            attrs['is_waitlist'] = False  

        return attrs
    
    def add_warning(self, message):
        print(f"Warning: {message}")

    def has_overlapping_bookings(self, pet, daycare, start_time, end_time):
        """Check if the pet has overlapping bookings at the same daycare or any daycare."""
        overlapping_bookings = Booking.objects.filter(
            pet=pet,
            daycare=daycare,
            start_time__lt=end_time,
            end_time__gt=start_time
        ).exists()

        if overlapping_bookings:
            return True
        
        return Booking.objects.filter(
            pet=pet,
            start_time__lt=end_time,
            end_time__gt=start_time
        ).exclude(daycare=daycare).exists()

    def is_daycare_open(self, daycare, start_time):
        """Check if the daycare is open on the day of the booking."""
        day_of_week = start_time.weekday() + 1  # Convert to 1-7 format (Monday = 1)
        opening_hours = OpeningHours.objects.filter(daycare=daycare, day=day_of_week).first()
        return opening_hours and not opening_hours.closed

    def is_within_opening_hours(self, daycare, start_time, end_time):
        """Check if the requested booking time is within the opening hours."""
        day_of_week = start_time.weekday() + 1
        opening_hours = OpeningHours.objects.filter(daycare=daycare, day=day_of_week).first()

        if opening_hours and opening_hours.from_hour and opening_hours.to_hour:
            opening_start = timezone.datetime.combine(start_time.date(), opening_hours.from_hour).replace(tzinfo=None)
            opening_end = timezone.datetime.combine(end_time.date(), opening_hours.to_hour).replace(tzinfo=None)

            start_time_naive = start_time.replace(tzinfo=None)
            end_time_naive = end_time.replace(tzinfo=None)

            if start_time_naive.time() < opening_start.time() or end_time_naive.time() > opening_end.time():
                return False
        return True
    
    def has_capacity(self, daycare, start_time, end_time):
        """Check if the daycare has capacity for the requested booking time."""
        day_of_week = start_time.weekday() + 1
        opening_hours = OpeningHours.objects.filter(daycare=daycare, day=day_of_week).first()

        if opening_hours and opening_hours.capacity > 0:
            current_bookings_count = Booking.objects.filter(
                daycare=daycare,
                start_time__lt=end_time,
                end_time__gt=start_time
            ).count()

            return current_bookings_count < opening_hours.capacity
        
        return False
    

class BookingWaitlistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = ['id', 'customer', 'pet', 'daycare', 'start_time', 'end_time', 'status', 'is_active', 'recurrence', 'products', 'customer_details', 'pet_details', 'checked_in', 'is_waitlist', 'waitlist_accepted']
        read_only_fields = ['status']
    

class CustomerNameSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    pets = serializers.SerializerMethodField()

    class Meta:
        model = CustomerProfile
        fields = ['id', 'first_name', 'last_name', 'username', 'pets']

    def get_pets(self, obj):
        return BasicPetNameSerializer(obj.pets.all(), many=True).data


class BlacklistedPetSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlacklistedPet
        fields = ['id', 'pet', 'daycare', 'reason', 'date_blacklisted', 'is_active']


class WaitlistSerializer(serializers.ModelSerializer):
    booking = serializers.SerializerMethodField()
    class Meta:
        model = Waitlist
        fields = ['id', 'booking', 'customer_notified', 'waitlisted_at', 'customer_accepted', 'is_active']

    def get_booking(self, obj):
        return BookingSerializer(obj.booking).data
    
    # need to make smaller booking serializer with just daycare name, pet and finer details just for waitlist display

class PostSerializer(serializers.ModelSerializer):
    tagged_pets = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Pet.objects.all(), required=False  
    )

    class Meta:
        model = Post
        fields = ['id', 'user', 'daycare', 'caption', 'date_time_created', 'is_active', 'status', 'tagged_pets']
        read_only_fields = ['user', 'status']

    def validate_tagged_pets(self, tagged_pets):
        # Ensure we return only the IDs in the validated data
        return [pet.id for pet in tagged_pets]


class LikeSerilaizer(serializers.ModelSerializer):
    class Meta:
        model = Like
        fields = ['id', 'user', 'post']


class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ['id', 'user', 'post', 'text', 'is_active', 'date_time_created']
