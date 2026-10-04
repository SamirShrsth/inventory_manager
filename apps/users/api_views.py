from django.contrib.auth import get_user_model
from rest_framework import generics, status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.permissions import IsAdminRole
from apps.users.serializers import (
    AdminUserSerializer,
    ChangePasswordSerializer,
    MeUpdateSerializer,
    RegisterSerializer,
    UserSerializer,
)

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        serializer = MeUpdateSerializer(request.user.profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user).data)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Password updated."}, status=status.HTTP_200_OK)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.select_related("profile").prefetch_related("assigned_warehouses")
    serializer_class = AdminUserSerializer
    permission_classes = [IsAdminRole]
    http_method_names = ["get", "post", "patch", "head", "options"]
    search_fields = ["email", "username", "profile__full_name"]
    filterset_fields = ["role", "is_active"]
    ordering_fields = ["email", "date_joined", "role"]
