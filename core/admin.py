from django.contrib import admin
from core.models import *

class StaffProfileInline(admin.TabularInline):  # or admin.StackedInline for different display
    model = StaffProfile.daycares.through
    verbose_name_plural = 'Staff Profiles'
    extra = 1


# Register your models here.
@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display = ('user_full_name', 'user_username', 'role', 'phone', 'is_active', 'daycares_names')
    list_filter = ('role',)  # Add filters as needed
    search_fields = ('user__first_name', 'user__last_name', 'user__username')
    raw_id_fields = ('user',)  # Use raw_id_fields for ForeignKey fields if needed

    def user_full_name(self, obj):
        return obj.user.get_full_name()
    user_full_name.short_description = 'Full Name'  # Customize column header

    def user_username(self, obj):
        return obj.user.username
    user_username.short_description = 'Username'  # Customize column header

    def daycares_names(self, obj):
        # This method will display a list of daycare names for the given staff profile
        return ", ".join(daycare.daycare_name for daycare in obj.daycares.all())

    daycares_names.short_description = 'Daycares'  # Optional: Add a short description for the column


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ('user_full_name', 'user_username', 'phone')
    search_fields = ('user__first_name', 'user__last_name', 'user__username', 'phone')

    def user_full_name(self, obj):
        return obj.user.get_full_name()
    user_full_name.short_description = 'Full Name'  # Customize column header

    def user_username(self, obj):
        return obj.user.username
    user_username.short_description = 'Username'  # Customize column header


@admin.register(Daycare)
class DaycareAdmin(admin.ModelAdmin):
    list_display = ('daycare_name', 'street_address', 'suburb', 'state', 'postcode', 'phone', 'email', 'owner_list')
    list_filter = ('state',)  # Add filters as needed
    search_fields = ('daycare_name', 'street_address', 'suburb', 'state', 'postcode', 'phone', 'email')
    inlines = [StaffProfileInline]

    def owner_list(self, obj):
        owners = StaffProfile.objects.filter(daycares=obj, role='O')
        return ", ".join(owner.user.get_full_name() for owner in owners)
    owner_list.short_description = 'Owners'


