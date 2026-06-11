
import resend
from celery import shared_task
from django.conf import settings
from .models import PasswordResetRequest,Usuario


resend.api_key = settings.RESEND_API_KEY

import secrets
from django.utils import timezone

@shared_task(bind=True, max_retries=3)
def enviar_email_boas_vindas(self, usuario_email, usuario_nome):
    try:
        resend.api_key = settings.RESEND_API_KEY
        params = {
            "from": "onboarding@resend.dev",
            "to": [usuario_email],
            "subject": "Bem-vindo à nossa plataforma!",
            "html": f"""
                <div>
                    <h1>Olá, {usuario_nome}!</h1>
                    <p>Seu cadastro foi realizado com sucesso.</p>
                </div>
            """
        }

        # O envio acontece via requisição HTTP para a API do Resend
        resposta = resend.Emails.send(params)
        
        return f"E-mail enviado via Resend. ID: {resposta.get('id')}"

    except Exception as e:
        # Se der erro de conexão/API, o Celery tenta novamente em 60 segundos
        raise self.retry(exc=e, countdown=60)
    


@shared_task(bind=True, max_retries=3)
def send_redefinition_email(self, user_email, user_name, token):
    try:
        resend.api_key = settings.RESEND_API_KEY
        params = {
            "from": "onboarding@resend.dev",
            "to": [user_email],
            "subject": "Redefinição de Senha",
            "html": f"""
                <div>
                    <h1>Olá, {user_name}!</h1>
                    <p>Solicitamos a redefinição da sua senha.</p>
                    <p>Use o seguinte token para redefinir sua senha: </p>
                    <h3><strong>{token}</strong></h3>
                </div>
            """
        }

        
        resposta = resend.Emails.send(params)

        return f"E-mail enviado via Resend. ID: {resposta.get('id')}"

    except Exception as e:
        # Se der erro de conexão/API, o Celery tenta novamente em 60 segundos
        raise self.retry(exc=e, countdown=60)



@shared_task(bind=True, max_retries=3)
def generate_reset_password_link(self,user_id):
    try:
        # 1. Gera um token seguro e único
        secure_token = secrets.token_urlsafe(32)
        user = Usuario.objects.get(pk=user_id)
        # 2. Salva a requisição no banco de dados
        reset_request = PasswordResetRequest.objects.create(
                usuario=user,
                token=secure_token
            )
        
        # 3. Monta o link (substitua pelo domínio real do seu front-end ou back-end)
        dominio = "http://localhost:8003"
        link = f"{dominio}/api/reset-password?token={reset_request.token}"

        send_redefinition_email.delay(
                user_email=user.email, 
                user_name=user.nome,  # Ou usuario.nome dependendo do seu model
                link=link
            )
        
        return f"Link gerado para {user.email} e enviado para a fila de e-mails."
    except Exception as e:
        raise self.retry(exc=e, countdown=60)