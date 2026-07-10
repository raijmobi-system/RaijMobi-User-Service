import json
from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.views.decorators.csrf import csrf_exempt

# REST Framework imports
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

# Google Auth
from google.oauth2 import id_token
from google.auth.transport import requests

# Easy Audit
from easyaudit.models import CRUDEvent

# Modelos e Serializadores Locais
from .models import Usuario, PasswordResetRequest, Perfil
from .serializers import UserRegistrationSerializer, UserProfileSerializer

# Métricas Prometheus
from .metrics import (
    users_total,
    drivers_total,
    passengers_total,
    logouts_total,
    google_logins_total,
    password_reset_requests_total
)

User = get_user_model()


# ==========================================
# 1. CADASTRO DE USUÁRIO
# ==========================================
class UserRegistrationView(generics.CreateAPIView):
    queryset = Usuario.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

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


# ==========================================
# 2. PERFIL DE USUÁRIO
# ==========================================
class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]  # importante para upload de foto

    def get_object(self):
        return self.request.user.perfil


# ==========================================
# 3. LOGOUT E SISTEMA DE SESSÃO
# ==========================================
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


# ==========================================
# 4. AUTENTICAÇÃO GOOGLE
# ==========================================
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
            print(f"❌ ERRO REAL DA VALIDAÇÃO GOOGLE: {e}")
            return Response(
                {"detail": f"Token Google inválido: {str(e)}"}, 
                status=status.HTTP_400_BAD_REQUEST
            )


# ==========================================
# 5. COMPLETAR PERFIL (PÓS-GOOGLE)
# ==========================================
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
            
            # Força a validação explícita
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
            print(f"❌ ERRO REAL AO SALVAR PERFIL: {e}")
            
            mensagem_erro = str(e)
            if hasattr(e, 'message_dict'):
                mensagem_erro = e.message_dict
            elif hasattr(e, 'messages'):
                mensagem_erro = e.messages

            return Response(
                {"detail": mensaje_erro}, 
                status=status.HTTP_400_BAD_REQUEST
            )


# ==========================================
# 6. REDEFINIÇÃO DE SENHA
# ==========================================
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


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
@csrf_exempt
def reset_password_view(request):
    # 1. RECONHECIMENTO DO LINK (Método GET)
    if request.method == 'GET':
        token_url = request.GET.get('token')
        
        if not token_url:
            return JsonResponse({'error': 'Token ausente.'}, status=400)
            
        try:
            reset_req = PasswordResetRequest.objects.get(token=token_url)
            
            if reset_req.used_at is not None:
                return JsonResponse({'error': 'Este link já foi utilizado.'}, status=400)
            if reset_req.is_expired(hours_valid=2):
                return JsonResponse({'error': 'Este link expirou.'}, status=400)
                
            return JsonResponse({'message': 'Token válido. Prossiga para a alteração de senha.'}, status=200)
            
        except PasswordResetRequest.DoesNotExist:
            return JsonResponse({'error': 'Token inválido.'}, status=404)

    # 2. PROCESSAMENTO DA NOVA SENHA (Método POST)
    elif request.method == 'POST':
        token_url = request.GET.get('token')
        data = json.loads(request.body)
        nova_senha = data.get('nova_senha')
        
        try:
            reset_req = PasswordResetRequest.objects.get(token=token_url)
            
            if reset_req.used_at or reset_req.is_expired():
                return JsonResponse({'error': 'Operação inválida ou expirada.'}, status=400)
            
            usuario = reset_req.usuario
            usuario.set_password(nova_senha)
            usuario.save()
            
            reset_req.used_at = timezone.now()
            reset_req.save()
            
            return JsonResponse({'success': 'Senha alterada com sucesso!'})
            
        except PasswordResetRequest.DoesNotExist:
            return JsonResponse({'error': 'Token inválido.'}, status=404)


# ==========================================
# 7. LOGS DE AUDITORIA DO ADMIN (EASY-AUDIT)
# ==========================================
class AdminLogsView(APIView):
    """
    Endpoint para retornar os logs de auditoria salvos pelo django-easy-audit.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        try:
            busca = request.query_params.get('busca', '')
            
            # Puxa os logs ordenados pelo mais recente
            eventos = CRUDEvent.objects.all().order_by('-datetime')

            if busca and busca.strip() != "":
                eventos = eventos.filter(object_repr__icontains=busca)

            dados_logs = []
            
            # Limitador preventivo de performance (últimos 50 itens)
            for ev in eventos[:50]:
                try:
                    # Converte de forma segura o timezone do banco para o local
                    data_local = timezone.localtime(ev.datetime)
                    data_str = data_local.strftime('%d/%m/%Y')
                    hora_str = data_local.strftime('%H:%M:%S')
                except Exception:
                    data_str = "N/A"
                    hora_str = "N/A"

                # Trata o campo de usuário defensivamente contra nulos
                usuario_nome = "Sistema"
                if ev.user:
                    usuario_nome = getattr(ev.user, 'nome', getattr(ev.user, 'email', str(ev.user)))

                dados_logs.append({
                    "id": ev.id,
                    "quem_mexeu": usuario_nome,
                    "data": data_str,
                    "hora": hora_str,
                    "microsservico": "User Service",
                    "acao": ev.get_event_type_display() if hasattr(ev, 'get_event_type_display') else "Alteração",
                    "no_que_mexeu": str(ev.object_repr)
                })

            return Response(dados_logs, status=status.HTTP_200_OK)

        except Exception as e:
            # Captura a falha para evitar que o Kong Gateway envie o erro genérico 502
            return Response({"erro": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)