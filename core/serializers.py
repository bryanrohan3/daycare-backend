from rest_framework import serializers
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from .models import *
from django.utils.dateparse import parse_datetime


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



class CustomerProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = CustomerProfile
        fields = ['id', 'user', 'phone', 'is_active']

    def create(self, validated_data):
        user_data = validated_data.pop('user')
        user = UserSerializer().create(user_data)
        customer_profile = CustomerProfile.objects.create(user=user, **validated_data)
        
        return customer_profile


class CustomerBasicProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerProfile
        fields = ['id', 'user']  # Add other fields you want to include
    

class OpeningHoursSerializer(serializers.ModelSerializer):
    day_name = serializers.SerializerMethodField()

    class Meta:
        model = OpeningHours
        fields = ['day', 'day_name', 'from_hour', 'to_hour', 'closed']

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

        # Update the fields of the Daycare instance
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Handle the nested OpeningHours
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


class PetSerializer(serializers.ModelSerializer):
    pet_types_display = serializers.SerializerMethodField()
    customers = serializers.SerializerMethodField()  
    
    class Meta:
        model = Pet
        fields = ['id', 'pet_name', 'pet_types', 'pet_bio', 'is_public', 'is_active', 'pet_types_display', 'customers']
        extra_kwargs = {
            'is_active': {'default': True},
            'is_public': {'default': True},
        }

    def get_pet_types_display(self, obj):
        return obj.get_pet_types_display()

    def get_customers(self, obj):
        # Retrieving the customers associated with the pet
        return [{
            'id': customer.id,
            'full_name': customer.user.get_full_name(),
            'phone': customer.phone,
            'email': customer.user.email
        } for customer in obj.customers.all()]

    def create(self, validated_data):
        if not isinstance(validated_data['pet_types'], list):
            validated_data['pet_types'] = [validated_data['pet_types']]
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if 'pet_types' in validated_data and not isinstance(validated_data['pet_types'], list):
            validated_data['pet_types'] = [validated_data['pet_types']]
        return super().update(instance, validated_data)



class PetNoteSerializer(serializers.ModelSerializer):
    pet = serializers.PrimaryKeyRelatedField(queryset=Pet.objects.all())
    employee = serializers.PrimaryKeyRelatedField(queryset=StaffProfile.objects.all())

    class Meta:
        model = PetNote
        fields = ['id', 'pet', 'employee', 'note', 'is_private']

    def create(self, validated_data):
        return PetNote.objects.create(**validated_data)
