from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.db.models import QuerySet


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email: str, password: str | None, **extra_fields):
        if not email:
            raise ValueError("An email address is required.")
        email = self.normalize_email(email)
        extra_fields.setdefault("username", email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault("role", User.Roles.VIEWER)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("role", User.Roles.ADMIN)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    class Roles(models.TextChoices):
        ADMIN = "admin", "Admin"
        STAFF = "staff", "Staff"
        VIEWER = "viewer", "Viewer"

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Roles.choices, default=Roles.VIEWER)
    assigned_warehouses = models.ManyToManyField(
        "inventory.Warehouse",
        blank=True,
        related_name="assigned_users",
    )

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        ordering = ["email"]
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["role"]),
        ]

    def save(self, *args, **kwargs):
        if self.is_superuser:
            self.role = self.Roles.ADMIN
            self.is_staff = True
        if not self.username:
            self.username = self.email
        super().save(*args, **kwargs)

    def is_admin_role(self) -> bool:
        return self.role == self.Roles.ADMIN or self.is_superuser

    def is_staff_role(self) -> bool:
        return self.role == self.Roles.STAFF

    def can_mutate(self) -> bool:
        return self.is_admin_role() or self.is_staff_role()

    def can_mutate_warehouse(self, warehouse) -> bool:
        if self.is_admin_role():
            return True
        if not self.is_staff_role():
            return False
        return self.assigned_warehouses.filter(pk=warehouse.pk).exists()

    def warehouse_queryset(self) -> QuerySet:
        from apps.inventory.models import Warehouse

        qs = Warehouse.objects.all()
        if self.is_admin_role() or self.role == self.Roles.VIEWER:
            return qs
        return qs.filter(assigned_users=self)


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    full_name = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    job_title = models.CharField(max_length=120, blank=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.full_name or self.user.email
