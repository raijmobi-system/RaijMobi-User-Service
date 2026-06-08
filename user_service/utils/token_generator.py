import resend
from django.conf import settings
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator

def enviar_email_verificacao_motorista(usuario):
    resend.api_key = settings.RESEND_API_KEY
    
    # Codifica o ID do usuário em Base64 para a URL
    uid = urlsafe_base64_encode(force_bytes(usuario.pk))
    # Gera o token seguro
    token = default_token_generator.make_token(usuario)
    
    # Esta rota existirá no seu frontend (ex: Next.js App Router)
    # Ex: http://localhost:3000/auth/verificar-email?uid=...&token=...
    link_verificacao = f"{settings.FRONTEND_URL}/auth/verificar-email/{uid}/{token}/"

    params = {
        "from": "Sua App <onboarding@seudominio.com.br>",
        "to": [usuario.email],
        "subject": "Confirme seu email para ativar seu perfil de Motorista",
        "html": f"""
            <h2>Olá, {usuario.nome}!</h2>
            <p>Para concluir seu cadastro como motorista, precisamos confirmar seu email.</p>
            <a href='{link_verificacao}'>Clique aqui para confirmar</a>
            <p>Se você não solicitou este cadastro, apenas ignore este email.</p>
        """
    }
    
    try:
        resend.Emails.send(params)
    except Exception as e:
        # Aqui você pode integrar com um logger (ex: Sentry ou logger padrão)
        print(f"Erro ao enviar email: {e}")