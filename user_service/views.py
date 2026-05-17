from rest_framework import status, generics, permissions
from rest_framework.parsers import MultiPartParser, FormParser
from .models import Usuario
from .serializers import (
    UserRegistrationSerializer,
    UserProfileSerializer,
)
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.response import Response
from rest_framework.views import APIView

# class UserRegistrationView(generics.CreateAPIView):
#     queryset = Usuario.objects.all()
#     serializer_class = UserRegistrationSerializer
#     permission_classes = [permissions.AllowAny]
#     parser_classes = [MultiPartParser, FormParser]

#     def create(self, request, *args, **kwargs):
#         response = super().create(request, *args, **kwargs)
#         # Dados que queremos enviar (garanta que o serializer já criou o usuário e o perfil)
#         user = Usuario.objects.get(pk=response.data.get('id'))  # ou pegue da resposta
#         perfil = user.perfil
#         user_data = {
#             'id': str(user.id),
#             'name': user.nome,
#             'email': user.email,
#             'is_rider': perfil.tipo_usuario == 'Passageiro',  # ajuste conforme sua regra
#             # outros campos se necessário (telefone, etc.)
#         }
#         try:
#             send_user_created_event(user_data)
#         except Exception as e:
#             # log do erro, mas não interrompe a resposta HTTP
#             print(f"Erro ao enviar evento Kafka: {e}")
#         return response


class UserRegistrationView(generics.CreateAPIView):
    queryset = Usuario.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    def perform_create(self, serializer):
        user = serializer.save()   # já cria usuário + perfil
        perfil = user.perfil
        user_data = {
            'id': str(user.id),
            'name': user.nome,
            'email': user.email,
            'is_rider': perfil.tipo_usuario == 'Passageiro',
        }
        try:
            from .kafka_producer import send_user_created_event
            send_user_created_event(user_data)
        except Exception as e:
            print(f"Erro ao enviar evento Kafka: {e}")
            
class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]  # importante para upload de foto

    def get_object(self):
        return self.request.user.perfil

# ... suas outras views

class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if not refresh_token:
                return Response({"detail": "Refresh token é obrigatório."}, status=status.HTTP_400_BAD_REQUEST)
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"detail": "Logout realizado com sucesso."}, status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)