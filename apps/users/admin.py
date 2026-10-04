from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from apps.users.models import Profile, User


class ProfileInline(admin.StackedInline):
    model = Profile
    extra = 0


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    inlines = [ProfileInline]
    ordering = ["email"]
    list_display = ("email", "role", "is_active", "is_superuser", "date_joined")
    list_filter = ("role", "is_active", "is_superuser")
    search_fields = ("email", "username", "first_name", "last_name")
    filter_horizontal = ("assigned_warehouses", "groups", "user_permissions")
    fieldsets = (
        (None, {"fields": ("email", "username", "password")}),
        ("Role", {"fields": ("role", "assigned_warehouses", "is_active", "is_staff", "is_superuser")}),
        ("Personal", {"fields": ("first_name", "last_name")}),
        ("Dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "username", "role", "password1", "password2"),
            },
        ),
    )


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "full_name", "job_title", "phone")
    search_fields = ("full_name", "user__email")
