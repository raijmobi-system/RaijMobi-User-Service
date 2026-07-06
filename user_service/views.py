from rest_framework import status, generics, permissions
from rest_framework.parsers import MultiPartParser, FormParser,JSONParser
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework import permissions
import json


from .models import Usuario, PasswordResetRequest,Perfil

from .metrics import users_total,drivers_total,passengers_total
from .metrics import logouts_total,google_logins_total,password_reset_requests_total

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
    parser_classes = [MultiPartParser, FormParser,JSONParser]

    def perform_create(self, serializer):
        user = serializer.save()   # já cria usuário + perfil
        perfil = user.perfil

        users_total.inc()

        if perfil.is_motorista:
            drivers_total.inc()
        else:
            passengers_total.inc()

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
    parser_classes = [MultiPartParser, FormParser, JSONParser]  # importante para upload de foto

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
            logouts_total.inc()
            return Response({"detail": "Logout realizado com sucesso."}, status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
class GoogleLoginView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        token = request.data.get("token")
        if not token:
            return Response({"detail": "Token não informado"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            google_data = id_token.verify_oauth2_token(
                token,
                requests.Request(),
                settings.GOOGLE_CLIENT_ID,
            )

            if not google_data.get("email_verified"):
                return Response({"detail": "E-mail não verificado pelo Google"}, status=status.HTTP_400_BAD_REQUEST)

            email = google_data["email"]
            nome = google_data.get("name", "")

            user, created = Usuario.objects.get_or_create(
                email=email,
                defaults={"nome": nome}
            )

            refresh = RefreshToken.for_user(user)
            google_logins_total.inc()

            # Verifica se o usuário já possui perfil criado
            has_profile = hasattr(user, 'perfil')

            return Response({
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "is_new_user": created or not has_profile, # Front-end usa isso para redirecionar
            })

        except ValueError as e:
            # 🌟 IMPRIME O ERRO NO TERMINAL DO DOCKER:
            print(f"❌ ERRO REAL DA VALIDAÇÃO GOOGLE: {e}")
            # 🌟 RETORNA O ERRO PRO FRONTEND VER NO ALERT:
            return Response(
                {"detail": f"Token Google inválido: {str(e)}"}, 
                status=status.HTTP_400_BAD_REQUEST
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

        password_reset_requests_total.inc()

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
        

# Adicione no seu views.py

class CompleteProfileView(APIView):
    """
    Endpoint para usuários cadastrados via Google completarem o perfil
    (Enviando CPF, Telefone e Tipo de Usuário).
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        print("📦 DADOS CHEGANDO NO COMPLETE PROFILE:", request.data)
        user = request.user

        # 1. Verifica se já possui perfil
        if hasattr(user, 'perfil'):
            return Response(
                {"detail": "Este usuário já possui um perfil completo."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        cpf = request.data.get("cpf")
        telefone = request.data.get("telefone")
        tipo_usuario = request.data.get("tipo_usuario")

        if not all([cpf, telefone, tipo_usuario]):
            return Response(
                {"detail": "CPF, telefone e tipo de usuário são obrigatórios."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # 2. Cria a instância do perfil
            perfil = Perfil(
                usuario=user,
                cpf=cpf,
                telefone=telefone,
                tipo_usuario=tipo_usuario,
                foto=request.FILES.get("foto", None),
                is_motorista=(tipo_usuario == 'Motorista')
            )
            
            # 🌟 Força a validação explícita (dispara o validar_cpf para capturar mensagens claras)
            perfil.full_clean()
            perfil.save()

            # 3. Dispara evento Kafka
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
                print(f"⚠️ Erro ao enviar evento Kafka no CompleteProfile: {e}")

            return Response({"detail": "Perfil completado com sucesso!"}, status=status.HTTP_201_CREATED)

        except Exception as e:
            # 🌟 IMPRIME O ERRO EXATO NO TERMINAL DO DOCKER:
            print(f"❌ ERRO REAL AO SALVAR PERFIL: {e}")
            
            # Formata a mensagem de erro para o Frontend
            mensagem_erro = str(e)
            if hasattr(e, 'message_dict'):
                mensagem_erro = e.message_dict
            elif hasattr(e, 'messages'):
                mensagem_erro = e.messages

            return Response(
                {"detail": mensagem_erro}, 
                status=status.HTTP_400_BAD_REQUEST
            )