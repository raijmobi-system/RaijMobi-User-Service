from rest_framework import status, generics, permissions
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
import json


from .models import Usuario, PasswordResetRequest

from google.oauth2 import id_token
from google.auth.transport import requests

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode

from .serializers import (
    UserRegistrationSerializer,
    UserProfileSerializer,
)

User = get_user_model()


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
            'is_driver': perfil.is_motorista, 
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
        
class GoogleLoginView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        token = request.data.get("token")

        if not token:
            return Response(
                {"detail": "Token não informado"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            google_data = id_token.verify_oauth2_token(
                token,
                requests.Request(),
                settings.GOOGLE_CLIENT_ID,
            )

            # Garantir que o email foi validado pelo Google
            if not google_data.get("email_verified"):
                return Response(
                    {"detail": "E-mail não verificado pelo Google"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            email = google_data["email"]
            nome = google_data.get("name", "")

            user = Usuario.objects.filter(email=email).first()

            if user is None:
                user = Usuario.objects.create_user(
                    email=email,
                    password=None,
                    nome=nome,
                )

            refresh = RefreshToken.for_user(user)

            return Response(
                {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                }
            )

        except ValueError:
            return Response(
                {"detail": "Token Google inválido"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        


class PasswordResetRequestView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get("email")

        if not email:
            return Response({"detail": "Email é obrigatório."}, status=status.HTTP_400_BAD_REQUEST)

        user = Usuario.objects.filter(email=email).first()

        if not user:
            return Response({"detail": "Usuário não encontrado."}, status=status.HTTP_404_NOT_FOUND)

        
        PasswordResetRequest.objects.create(usuario=user)

        return Response({"detail": "Solicitação de redefinição de senha enviada."}, status=status.HTTP_201_CREATED)
    


from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
@csrf_exempt # Se for uma API separada, ou use a proteção CSRF padrão se for um form Django
def reset_password_view(request):
    
    # 1. RECONHECIMENTO DO LINK (Método GET)
    # Quando o usuário clica no e-mail, ele abre essa rota via GET para renderizar a página ou checar se o link é válido
    if request.method == 'GET':
        token_url = request.GET.get('token')
        
        if not token_url:
            return JsonResponse({'error': 'Token ausente.'}, status=400)
            
        try:
            reset_req = PasswordResetRequest.objects.get(token=token_url)
            
            # Validações de segurança
            if reset_req.used_at is not None:
                return JsonResponse({'error': 'Este link já foi utilizado.'}, status=400)
            if reset_req.is_expired(hours_valid=2): # Usando o método que criamos no modelo
                return JsonResponse({'error': 'Este link expirou.'}, status=400)
                
            return JsonResponse({'message': 'Token válido. Prossiga para a alteração de senha.'}, status=200)
            
        except PasswordResetRequest.DoesNotExist:
            return JsonResponse({'error': 'Token inválido.'}, status=404)


    # 2. PROCESSAMENTO DA NOVA SENHA (Método POST)
    # Quando o usuário digita a nova senha na tela e clica em "Salvar"
    elif request.method == 'POST':
        token_url = request.GET.get('token') # Também pega o token da URL no envio do form
        data = json.loads(request.body)
        nova_senha = data.get('nova_senha')
        
        try:
            reset_req = PasswordResetRequest.objects.get(token=token_url)
            
            # Repete as checagens por segurança antes de salvar a senha
            if reset_req.used_at or reset_req.is_expired():
                return JsonResponse({'error': 'Operação inválida ou expirada.'}, status=400)
            
            # Atualiza a senha do usuário associado
            usuario = reset_req.usuario
            usuario.set_password(nova_senha)
            usuario.save()
            
            # Invalida o token para não ser reutilizado
            reset_req.used_at = timezone.now()
            reset_req.save()
            
            return JsonResponse({'success': 'Senha alterada com sucesso!'})
            
        except PasswordResetRequest.DoesNotExist:
            return JsonResponse({'error': 'Token inválido.'}, status=404)