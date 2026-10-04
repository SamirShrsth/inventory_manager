from django.urls import path

from apps.users import views

app_name = "users"

urlpatterns = [
    path("login/", views.UserLoginView.as_view(), name="login"),
    path("logout/", views.UserLogoutView.as_view(), name="logout"),
    path("register/", views.RegisterView.as_view(), name="register"),
    path("profile/", views.ProfileView.as_view(), name="profile"),
    path("profile/password/", views.UserPasswordChangeView.as_view(), name="password-change"),
    path("users/", views.UserListView.as_view(), name="user-list"),
    path("users/new/", views.UserCreateView.as_view(), name="user-create"),
    path("users/<int:pk>/edit/", views.UserUpdateView.as_view(), name="user-update"),
]
