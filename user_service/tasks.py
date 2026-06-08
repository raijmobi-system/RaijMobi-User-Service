
import resend
from celery import shared_task
from django.conf import settings


resend.api_key = settings.RESEND_API_KEY


@shared_task(bind=True, max_retries=3)
def enviar_email_boas_vindas(self, usuario_email, usuario_nome):
    try:
        params = {
            "from": "Sua Empresa <nao-responda@raijmobi.com>",
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
    

   
