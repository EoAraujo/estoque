from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth import get_user_model

from .models import UserProfile

User = get_user_model()


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    extra = 0
    fk_name = "user"


class CustomUserAdmin(UserAdmin):
    inlines = (UserProfileInline,)
    list_display = ("username", "email", "first_name", "last_name", "is_active", "is_staff")
    list_filter = ("is_active", "is_staff", "is_superuser")


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
