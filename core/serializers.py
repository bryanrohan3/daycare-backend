from rest_framework import serializers
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from .models import *


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
        return DaycareSerializer(obj.daycares.all(), many=True).data

    def create(self, validated_data):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("Authentication credentials were not provided.")

        creator_profile = StaffProfile.objects.get(user=request.user)
        if creator_profile.role != 'O':
            raise serializers.ValidationError("Only Owners can create new profiles.")

        user_data = validated_data.pop('user')
        daycares = validated_data.pop('daycares', [])

        # Debugging statements
        print(f"Creator Profile: {creator_profile}")
        print(f"Creator Daycare IDs: {creator_profile.daycares.values_list('id', flat=True)}")
        print(f"Received Daycares: {daycares}")

        # Validate daycares
        if daycares:
            # Convert daycares to a list of IDs for validation
            daycare_ids = [daycare.id for daycare in daycares] if isinstance(daycares[0], Daycare) else daycares
            creator_daycare_ids = creator_profile.daycares.values_list('id', flat=True)
            print(f"Daycare IDs for Validation: {daycare_ids}")
            print(f"Creator Daycare IDs for Validation: {creator_daycare_ids}")
            if not all(daycare_id in creator_daycare_ids for daycare_id in daycare_ids):
                print("Daycare validation failed")
                raise serializers.ValidationError("You can only assign staff to daycares you are associated with.")

        # Create or get the user instance
        user_serializer = UserSerializer(data=user_data)
        user_serializer.is_valid(raise_exception=True)
        user = user_serializer.save()

        staff_profile = StaffProfile.objects.create(user=user, **validated_data)
        staff_profile.daycares.set(daycare_ids)  # Set daycares for the new staff profile

        return staff_profile



    

class BasicStaffProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = StaffProfile
        fields = ['user', 'role', 'phone', 'is_active']


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
        fields = ['id', 'daycare_name', 'street_address', 'suburb', 'state', 'postcode', 'phone', 'email', 'staff', 'is_active', 'capacity', 'opening_hours', 'products', 'pet_types_display']

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
