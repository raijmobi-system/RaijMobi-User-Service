from django.db.models.signals import post_save
from .models import PasswordResetRequest
from django.contrib.auth import get_user_model
from django.dispatch import receiver



User = get_user_model()

@receiver(post_save, sender=PasswordResetRequest)
def redefine_password(sender, instance, created, **kwargs):
    """
    Função disparada LOGO APÓS o save do PasswordResetRequest.
    """
    if created:
        from .tasks import send_redefinition_email
        user = instance.usuario
        if user:
            send_redefinition_email.delay(
            user.email, 
            user.nome,  
            instance.token
        )
        else:
            print(f"Tentativa de redefinição para e-mail não cadastrado: {instance.email}")