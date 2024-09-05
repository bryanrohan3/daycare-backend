from rest_framework import serializers
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from .models import *


class UserSerializer(serializers.ModelSerializer):
    token = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'password', 'token', 'is_active']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user

    def get_token(self, obj):
        token, created = Token.objects.get_or_create(user=obj)
        return token.key

class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()


class StaffProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = StaffProfile
        fields = ['id', 'user', 'role', 'phone', 'is_active']

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