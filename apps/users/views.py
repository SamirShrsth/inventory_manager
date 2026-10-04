from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, FormView, ListView, UpdateView

from apps.core.mixins import AdminRequiredMixin
from apps.users.forms import AdminUserForm, EmailAuthenticationForm, ProfileForm, RegisterForm, StyledPasswordChangeForm
from apps.users.models import User


class UserLoginView(LoginView):
    template_name = "users/login.html"
    authentication_form = EmailAuthenticationForm
    redirect_authenticated_user = True


class UserLogoutView(LogoutView):
    next_page = reverse_lazy("users:login")


class RegisterView(CreateView):
    form_class = RegisterForm
    template_name = "users/register.html"
    success_url = reverse_lazy("core:dashboard")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("core:dashboard")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        messages.success(self.request, "Account created. You are now signed in.")
        return response


class ProfileView(LoginRequiredMixin, FormView):
    template_name = "users/profile.html"
    form_class = ProfileForm
    success_url = reverse_lazy("users:profile")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.request.user.profile
        return kwargs

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Profile updated.")
        return super().form_valid(form)


class UserPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    form_class = StyledPasswordChangeForm
    template_name = "users/password_change.html"
    success_url = reverse_lazy("users:profile")

    def form_valid(self, form):
        messages.success(self.request, "Password changed.")
        return super().form_valid(form)


class UserListView(AdminRequiredMixin, ListView):
    model = User
    template_name = "users/user_list.html"
    paginate_by = 20
    queryset = User.objects.select_related("profile").prefetch_related("assigned_warehouses")


class UserCreateView(AdminRequiredMixin, CreateView):
    form_class = AdminUserForm
    template_name = "users/user_form.html"
    success_url = reverse_lazy("users:user-list")

    def form_valid(self, form):
        messages.success(self.request, "User created.")
        return super().form_valid(form)


class UserUpdateView(AdminRequiredMixin, UpdateView):
    model = User
    form_class = AdminUserForm
    template_name = "users/user_form.html"
    success_url = reverse_lazy("users:user-list")

    def form_valid(self, form):
        messages.success(self.request, "User updated.")
        return super().form_valid(form)
