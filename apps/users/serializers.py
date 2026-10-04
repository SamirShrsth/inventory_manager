from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.inventory.models import Warehouse
from apps.users.models import Profile

User = get_user_model()


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ("full_name", "phone", "job_title", "avatar")


class UserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(read_only=True)
    assigned_warehouses = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "username",
            "role",
            "is_active",
            "date_joined",
            "profile",
            "assigned_warehouses",
        )
        read_only_fields = fields


class AdminUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    assigned_warehouses = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Warehouse.objects.all(),
        required=False,
    )

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "role",
            "is_active",
            "password",
            "assigned_warehouses",
            "date_joined",
        )
        read_only_fields = ("id", "date_joined")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assigned_warehouses"].queryset = Warehouse.objects.all()

    def create(self, validated_data):
        warehouses = validated_data.pop("assigned_warehouses", [])
        password = validated_data.pop("password", None)
        if not password:
            raise serializers.ValidationError({"password": "Password is required."})
        user = User.objects.create_user(password=password, **validated_data)
        if warehouses:
            user.assigned_warehouses.set(warehouses)
        return user

    def update(self, instance, validated_data):
        warehouses = validated_data.pop("assigned_warehouses", None)
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        if warehouses is not None:
            instance.assigned_warehouses.set(warehouses)
        return instance


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    full_name = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ("email", "password", "password_confirm", "full_name")

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        from django.contrib.auth.password_validation import validate_password

        validate_password(attrs["password"])
        return attrs

    def create(self, validated_data):
        full_name = validated_data.pop("full_name", "")
        validated_data.pop("password_confirm")
        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            role=User.Roles.VIEWER,
        )
        user.profile.full_name = full_name
        user.profile.save(update_fields=["full_name", "updated_at"])
        return user


class MeUpdateSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True)
    job_title = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Profile
        fields = ("full_name", "phone", "job_title")


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate_new_password(self, value):
        from django.contrib.auth.password_validation import validate_password

        validate_password(value, self.context["request"].user)
        return value

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])
        return user
