from django.urls import path, include
from rest_framework.routers import DefaultRouter
from core import viewsets
from django.contrib import admin

# Define the router for standard CRUD endpoints
api_router = DefaultRouter()
api_router.register(r'users', viewsets.UserViewSet)
api_router.register(r'staff-profile', viewsets.StaffProfileViewSet)
api_router.register(r'customer-profile', viewsets.CustomerProfileViewSet)
api_router.register(r'daycare', viewsets.DaycareViewSet)
api_router.register(r'product', viewsets.ProductViewSet, basename='product')
api_router.register(r'roster', viewsets.RosterViewSet, basename='roster')
api_router.register(r'unavailability', viewsets.UnavailabilityViewSet, basename='unavailability')
api_router.register(r'pet', viewsets.PetViewSet, basename='pet')
api_router.register(r'pet-note', viewsets.PetNoteViewSet, basename='pet-note')
api_router.register(r'booking', viewsets.BookingViewSet, basename='booking')
api_router.register(r'blacklist', viewsets.BlacklistedPetViewSet, basename='blacklist')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(api_router.urls)),
]

urlpatterns += api_router.urls