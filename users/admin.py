from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Country, User

class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Thông tin quốc gia', {'fields': ('country',)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Thông tin quốc gia', {'fields': ('country',)}),
    )

admin.site.register(Country)
admin.site.register(User, CustomUserAdmin)