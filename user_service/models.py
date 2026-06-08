from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from .validators import validar_cpf
import uuid
from django.utils import timezone

from .manager import UsuarioManager


class Usuario(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    date_joined = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    objects = UsuarioManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nome']

    def __str__(self):
        return self.nome

    def get_full_name(self):
        return self.nome

    def get_short_name(self):
        return self.nome.split()[0] if self.nome else ''


class Perfil(models.Model):
    TIPO_CHOICES = [('Motorista', 'Motorista'), ('Passageiro', 'Passageiro')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, related_name='perfil')
    cpf = models.CharField(max_length=14, unique=True, validators=[validar_cpf])
    telefone = models.CharField(max_length=15)
    tipo_usuario = models.CharField(max_length=50, choices=TIPO_CHOICES)
    foto = models.ImageField(upload_to='fotos_perfil/', null=True, blank=True)
    is_motorista = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return f'Perfil de {self.usuario.nome}'

# usuarios/models.py (ou audit/models.py)
from django.db import models
from easyaudit.models import CRUDEvent
from django.contrib.contenttypes.models import ContentType

class UsuarioAudit(CRUDEvent):
    class Meta:
        proxy = True
        verbose_name = 'Auditoria de Usuário'
        verbose_name_plural = 'Auditorias de Usuários'

class PerfilAudit(CRUDEvent):
    class Meta:
        proxy = True
        verbose_name = 'Auditoria de Perfil'
        verbose_name_plural = 'Auditorias de Perfis'