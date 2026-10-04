from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, UserCreationForm

from apps.core.forms import apply_bootstrap
from apps.users.models import Profile, User


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(label="Email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_bootstrap(self)


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    full_name = forms.CharField(max_length=150, required=False)

    class Meta:
        model = User
        fields = ("email", "full_name", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_bootstrap(self)

    def save(self, commit: bool = True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.username = user.email
        user.role = User.Roles.VIEWER
        if commit:
            user.save()
            profile = user.profile
            profile.full_name = self.cleaned_data.get("full_name", "")
            profile.save(update_fields=["full_name", "updated_at"])
        return user


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ("full_name", "phone", "job_title", "avatar")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_bootstrap(self)


class StyledPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_bootstrap(self)


class AdminUserForm(forms.ModelForm):
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput,
        help_text="Leave blank to keep the current password.",
    )

    class Meta:
        model = User
        fields = (
            "email",
            "first_name",
            "last_name",
            "role",
            "is_active",
            "assigned_warehouses",
            "password",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_bootstrap(self)

    def clean_password(self):
        password = self.cleaned_data.get("password")
        if password:
            password_validation.validate_password(password, self.instance)
        elif not self.instance.pk:
            raise forms.ValidationError("Password is required for new users.")
        return password

    def save(self, commit: bool = True):
        user = super().save(commit=False)
        user.username = user.email
        password = self.cleaned_data.get("password")
        if password:
            user.set_password(password)
        if user.role == User.Roles.ADMIN:
            user.is_staff = True
        if commit:
            user.save()
            self.save_m2m()
        return user
