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
from .permissions import *
from django.utils.dateparse import parse_date
from django.utils import timezone


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
        user = self.request.user
        
        if hasattr(user, 'staffprofile'):
            staff_profile = user.staffprofile
            if staff_profile.role == 'O':
                # Owners can see all staff profiles
                return queryset
            else:
                # Employees can only see their own profile
                return queryset.filter(user=user)
        
        return queryset

    @action(detail=False, methods=['get'], url_path='current', permission_classes=[IsStaff])
    def current(self, request):
        """
        Retrieve the staff profile of the currently authenticated user.
        """
        user = request.user
        if hasattr(user, 'staffprofile'):
            serializer = self.get_serializer(user.staffprofile)
            return Response(serializer.data)
        return Response({'detail': 'Staff profile not found'}, status=status.HTTP_404_NOT_FOUND)
    

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
        queryset = Daycare.objects.all()  # Default queryset for all users

        if user.is_authenticated:
            if hasattr(user, 'staffprofile'):
                try:
                    staff_profile = user.staffprofile
                    # Staff filtering: only show daycares they work for
                    queryset = staff_profile.daycares.all()
                except StaffProfile.DoesNotExist:
                    pass

        # Apply search filter if present
        search_term = self.request.query_params.get('search', None)
        if search_term:
            queryset = queryset.filter(daycare_name__icontains=search_term)

        return queryset

    def get_serializer_class(self):
        # Use CustomerDaycareSerializer if search parameter is present
        if self.request.query_params.get('search'):
            return CustomerDaycareSerializer
        return super().get_serializer_class()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    

class ProductViewSet(viewsets.GenericViewSet, mixins.UpdateModelMixin, mixins.RetrieveModelMixin, mixins.ListModelMixin, mixins.CreateModelMixin):
    """
    A viewset for viewing and editing product instances.
    """
    serializer_class = ProductSerializer
    queryset = Product.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    
    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH', 'POST']:
            # Only allow owners to create products
            permission_classes = [IsOwner]
        else:
            permission_classes = [IsStaff]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        """
        Restrict the queryset to products that belong to daycares the authenticated user works at.
        """
        request = self.request
        if not request.user.is_authenticated:
            return Product.objects.none()

        # Get the daycares associated with the authenticated user
        staff_profile = StaffProfile.objects.get(user=request.user)
        user_daycare_ids = staff_profile.daycares.values_list('id', flat=True)

        # Filter products to only include those that belong to the user's associated daycares
        return Product.objects.filter(daycare__id__in=user_daycare_ids)

    def create(self, request, *args, **kwargs):
        """
        Handle product creation and validate that the user is associated with the daycare.
        """
        daycare_id = request.data.get('daycare')

        if not request.user.is_authenticated:
            return Response(
                {"error": "Authentication credentials were not provided."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if not daycare_id:
            return Response(
                {"error": "Daycare ID must be provided."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            staff_profile = StaffProfile.objects.get(user=request.user)
        except StaffProfile.DoesNotExist:
            return Response(
                {"error": "Staff profile not found."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if the user is an owner
        if staff_profile.role != 'O':
            return Response(
                {"error": "You do not have permission to create a product."},
                status=status.HTTP_403_FORBIDDEN
            )

        user_daycare_ids = staff_profile.daycares.values_list('id', flat=True)

        if int(daycare_id) not in user_daycare_ids:
            return Response(
                {"error": "You cannot create a product for a daycare you are not associated with."},
                status=status.HTTP_403_FORBIDDEN
            )

        return super().create(request, *args, **kwargs)


class RosterViewSet(viewsets.GenericViewSet, 
                    mixins.UpdateModelMixin, 
                    mixins.RetrieveModelMixin, 
                    mixins.ListModelMixin, 
                    mixins.CreateModelMixin):
    queryset = Roster.objects.all()
    serializer_class = RosterSerializer
    permission_classes = [IsOwner | IsStaff]

    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH', 'POST']:
            permission_classes = [IsOwner]
        else:
            permission_classes = [IsStaff]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Roster.objects.none()

        queryset = Roster.objects.none()

        if hasattr(user, 'staffprofile'):
            staff_profile = user.staffprofile
            queryset = Roster.objects.filter(staff=staff_profile, is_active=True)

            if staff_profile.role == 'O':
                owned_daycares = staff_profile.daycares.all()
                owner_queryset = Roster.objects.filter(daycare__in=owned_daycares, is_active=True)
                queryset = queryset | owner_queryset

        # Daycare filtering based on query parameters
        daycare_id = self.request.query_params.get('daycare', None)
        if daycare_id:
            queryset = queryset.filter(daycare__id=daycare_id)

        # Fetch date range from query parameters
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)

        if start_date and end_date:
            try:
                start_shift = parse_date(start_date)
                end_shift = parse_date(end_date)

                if start_shift and end_shift:
                    end_shift = timezone.datetime.combine(end_shift, timezone.datetime.max.time())
                    queryset = queryset.filter(start_shift__gte=start_shift, start_shift__lte=end_shift)

            except ValueError:
                return Roster.objects.none()  

        return queryset.distinct()

    @action(detail=True, methods=['patch'], url_path='deactivate')
    def deactivate(self, request, pk=None):
        try:
            roster = self.get_object()
            roster.is_active = False
            roster.save()
            return Response({"detail": "Roster deactivated successfully."}, status=status.HTTP_204_NO_CONTENT)
        except Roster.DoesNotExist:
            return Response({"detail": "Roster not found."}, status=status.HTTP_404_NOT_FOUND)


class UnavailabilityViewSet(viewsets.ModelViewSet):
    serializer_class = StaffUnavailabilitySerializer

    def get_queryset(self):
        user = self.request.user
        
        # Ensure the user is authenticated and has a staff profile
        if hasattr(user, 'staffprofile'):
            staff_profile = user.staffprofile
            
            # If the user is an owner, show unavailability for all active staff in the owner's daycares
            if staff_profile.role == 'O':
                owned_daycares = staff_profile.daycares.all()  # Fetch all daycares the owner is associated with
                return StaffUnavailability.objects.filter(staff__daycares__in=owned_daycares, is_active=True).distinct()
            else:
                # If the user is not an owner, only show their own active unavailability
                return StaffUnavailability.objects.filter(staff=staff_profile, is_active=True)
        
        # Return an empty queryset if the user does not have a staff profile
        return StaffUnavailability.objects.none()

    @action(detail=True, methods=['patch'], url_path='deactivate')
    def deactivate(self, request, pk=None):
        try:
            unavailability = self.get_object()
            unavailability.is_active = False
            unavailability.save()
            return Response({"detail": "Unavailability deactivated successfully."}, status=status.HTTP_204_NO_CONTENT)
        except StaffUnavailability.DoesNotExist:
            return Response({"detail": "Unavailability not found."}, status=status.HTTP_404_NOT_FOUND)

    def perform_create(self, serializer):
        request = self.request
        staff_profile = request.user.staffprofile
        serializer.save(staff=staff_profile)