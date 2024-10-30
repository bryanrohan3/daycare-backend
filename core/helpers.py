from rest_framework.exceptions import PermissionDenied

def user_has_staff_profile(user):
    """
    Check if the user has a staff profile.
    """
    return hasattr(user, 'staffprofile')


def user_has_customer_profile(user):
    """
    Check if the user has a customer profile.
    """
    return hasattr(user, 'customerprofile')