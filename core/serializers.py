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
    daycares = serializers.SerializerMethodField()
    daycares_names = serializers.SerializerMethodField()

    class Meta:
        model = StaffProfile
        fields = ['id', 'user', 'role', 'phone', 'is_active', 'daycares', 'daycares_names']

    def get_daycares(self, obj):
        return obj.daycares.values_list('id', flat=True)
    
    def get_daycares_names(self, instance):
        # Retrieve the dealerships associated with the profile
        return DaycareSerializer(instance.daycares.all(), many=True).data

    def create(self, validated_data):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("Authentication credentials were not provided.")

        # Ensure the creator is a Management Dealer
        creator_profile = StaffProfile.objects.get(user=request.user)
        if creator_profile.role != 'O':
            raise serializers.ValidationError("Only Owners can create Employee and Owner users.")

        user_data = validated_data.pop('user')

        user = UserSerializer().create(user_data)
        staff_profile = StaffProfile.objects.create(user=user, **validated_data)
        
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


class DaycareSerializer(serializers.ModelSerializer):
    staff = serializers.SerializerMethodField()
    opening_hours = OpeningHoursSerializer(many=True)

    class Meta:
        model = Daycare
        fields = ['id', 'daycare_name', 'street_address', 'suburb', 'state', 'postcode', 'phone', 'email', 'staff', 'is_active', 'capacity', 'opening_hours'] 

    def get_staff(self, obj):
        request = self.context.get('request')
        
        if not request:
            return []  # Return empty list if request is not found

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