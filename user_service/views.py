from rest_framework import status, generics, permissions
from rest_framework.parsers import MultiPartParser, FormParser
from .models import Usuario
from .serializers import (
    UserRegistrationSerializer,
    UserProfileSerializer,
)

class UserRegistrationView(generics.CreateAPIView):
    queryset = Usuario.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    parser_classes = [MultiPartParser, FormParser]

class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]  # importante para upload de foto

    def get_object(self):
        return self.request.user
