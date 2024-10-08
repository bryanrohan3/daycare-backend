from rest_framework import permissions
from .models import *

SAFE_METHODS = ('GET', 'HEAD', 'OPTIONS', 'POST')

# 1. IsOwner
class IsOwner(permissions.BasePermission):
    """
    Allows access only to management dealers.
    """
    def has_permission(self, request, view):
        # Check if the user is authenticated and has a dealer profile with management role
        return request.user and request.user.is_authenticated and (
            hasattr(request.user, 'staffprofile') and request.user.staffprofile.role == 'O'
        )

    def has_object_permission(self, request, view, obj):
        # Mirror the permission check for the `has_permission` method
        return self.has_permission(request, view)

# 2. IsEmployee
class IsEmployee(permissions.BasePermission):
    """
    Allows access only to sales dealers.
    """
    def has_permission(self, request, view):
        # Check if the user is authenticated and has a dealer profile with sales role
        return request.user and request.user.is_authenticated and (
            hasattr(request.user, 'staffprofile') and request.user.staffprofile.role == 'E'
        )

    def has_object_permission(self, request, view, obj):
        # Mirror the permission check for the `has_permission` method
        return self.has_permission(request, view)


# 3. IsStaff
class IsStaff(permissions.BasePermission):
    """
    Allows access only to dealers (either sales or management) from the same dealership.
    """
    def has_permission(self, request, view):
        # Check if the user is authenticated and has a dealer profile
        return request.user and request.user.is_authenticated and hasattr(request.user, 'staffprofile')

    def has_object_permission(self, request, view, obj):
        # Allow safe methods for everyone
        if request.method in SAFE_METHODS:
            return True
        
        # Check if the user is a dealer and belongs to the same dealership as the object
        if hasattr(request.user, 'staffprofile'):
            staff_profile = request.user.staffprofile
            return obj.daycare == staff_profile.daycare
        
        return False

# 4. IsCustomer
class IsCustomer(permissions.BasePermission):
    """
    Allows access only to wholesalers.
    """
    def has_permission(self, request, view):
        # Check if the user is authenticated and has a wholesaler profile
        return request.user and request.user.is_authenticated and hasattr(request.user, 'customerprofile')

    def has_object_permission(self, request, view, obj):
        # Allow any authenticated wholesaler to perform any action
        return True