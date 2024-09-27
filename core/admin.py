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

class OpeningHoursInline(admin.TabularInline):
    model = OpeningHours
    extra = 1
    fields = ('day', 'from_hour', 'to_hour', 'closed')
    verbose_name = 'Opening Hour'
    verbose_name_plural = 'Opening Hours'


class ProductsInline(admin.TabularInline):  # or use admin.StackedInline
    model = Product
    extra = 1
    fields = ('name', 'description', 'price', 'capacity')
    verbose_name = 'Product'
    verbose_name_plural = 'Products'


class DaycareAdmin(admin.ModelAdmin):
    list_display = ('daycare_name', 'street_address', 'suburb', 'state', 'postcode', 'phone', 'email', 'owner_list')
    list_filter = ('state',)
    search_fields = ('daycare_name', 'street_address', 'suburb', 'state', 'postcode', 'phone', 'email')
    inlines = [OpeningHoursInline, ProductsInline]

    def owner_list(self, obj):
        owners = StaffProfile.objects.filter(daycares=obj, role='O')
        return ", ".join(owner.user.get_full_name() for owner in owners)
    owner_list.short_description = 'Owners'


admin.site.register(Daycare, DaycareAdmin)


class ProductsAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'price', 'capacity', 'daycare__daycare_name')
    list_filter = ('daycare',)
    search_fields = ('name', 'description')

admin.site.register(Product, ProductsAdmin)


class RosterAdmin(admin.ModelAdmin):
    list_display = ('staff', 'daycare__daycare_name', 'start_shift', 'end_shift', 'shift_day')
    list_filter = ('daycare', 'shift_day')
    search_fields = ('staff__user__first_name', 'staff__user__last_name', 'daycare__daycare_name')
    raw_id_fields = ('staff', 'daycare')  # Use raw_id_fields for ForeignKey fields for better performance with large datasets

admin.site.register(Roster, RosterAdmin)


class StaffUnavailabilityAdmin(admin.ModelAdmin):
    list_display = ('staff', 'date', 'day_of_week', 'is_recurring')
    list_filter = ('is_recurring', 'day_of_week')
    search_fields = ('staff__user__first_name', 'staff__user__last_name')
    raw_id_fields = ('staff',)  # To optimize performance if you have many staff profiles

admin.site.register(StaffUnavailability, StaffUnavailabilityAdmin)


# Admin configuration for Pet
class PetAdmin(admin.ModelAdmin):
    list_display = ('pet_name', 'get_pet_types_display', 'is_public', 'is_active')
    search_fields = ('pet_name',)

    def get_pet_types_display(self, obj):
        """Display the pet types in the admin list view."""
        return ", ".join(obj.get_pet_types_display())
    get_pet_types_display.short_description = 'Pet Types'  # Optional: Set a custom column name

admin.site.register(Pet, PetAdmin)


# Admin configuration for PetNote
class PetNoteAdmin(admin.ModelAdmin):
    list_display = ('pet', 'employee', 'note', 'is_private')
    search_fields = ('pet__pet_name', 'employee__user__first_name', 'note')

admin.site.register(PetNote, PetNoteAdmin)