from django.shortcuts import render
from rest_framework import viewsets, mixins
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from .serializers import *
from rest_framework.decorators import action
from django.contrib.auth import authenticate, login
from rest_framework.response import Response
from rest_framework import status
from .models import *



# Create your views here.
class UserViewSet(viewsets.GenericViewSet, mixins.UpdateModelMixin, mixins.RetrieveModelMixin):
    """
    ViewSet for managing users.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer

    serializer_classes = {
        'login': UserLoginSerializer,
    }

    def get_serializer_class(self):
        """
        Return the class to use for the serializer based on the action.
        """
        if self.action == 'login':
            return self.serializer_classes.get('login', UserSerializer)
        return super().get_serializer_class()


    @action(detail=False, methods=['POST'], permission_classes=[])
    def login(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = authenticate(username=serializer.validated_data['username'], password=serializer.validated_data['password'])
        
        if user:
            if not user.is_active:
                return Response({'error': 'This account is inactive.'}, status=status.HTTP_403_FORBIDDEN)
                
            login(request, user)
            token, _ = Token.objects.get_or_create(user=user)
            return Response({'message': 'Login successful', 'user': UserSerializer(user).data, 'token': token.key})
        else:
            return Response({'error': 'Invalid username or password'}, status=status.HTTP_400_BAD_REQUEST)


class StaffProfileViewSet(viewsets.GenericViewSet, mixins.UpdateModelMixin, mixins.RetrieveModelMixin, mixins.ListModelMixin, mixins.CreateModelMixin):
    queryset = StaffProfile.objects.all()
    serializer_class = StaffProfileSerializer

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return StaffProfile.objects.none()
        
        queryset = super().get_queryset()
        user = self.request.user # I Will Use this to Check for StaffProfile in Daycare

        return queryset
    

class CustomerProfileViewSet(viewsets.GenericViewSet, mixins.UpdateModelMixin, mixins.RetrieveModelMixin, mixins.ListModelMixin, mixins.CreateModelMixin):
    queryset = CustomerProfile.objects.all()
    serializer_class = CustomerProfileSerializer

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return CustomerProfile.objects.none()
        
        queryset = super().get_queryset()
        user = self.request.user

        return queryset
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.user != request.user:
            return Response({'error': 'You do not have permission to view this customer profile.'}, status=status.HTTP_403_FORBIDDEN)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class DaycareViewSet(viewsets.GenericViewSet, mixins.UpdateModelMixin, mixins.RetrieveModelMixin, mixins.ListModelMixin, mixins.CreateModelMixin):
    queryset = Daycare.objects.all()
    serializer_class = DaycareSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = Daycare.objects.none()

        if user.is_authenticated:
            try:
                staff_profile = user.staffprofile
                queryset = staff_profile.daycares.all()
            except StaffProfile.DoesNotExist:
                pass

        return queryset
    
    