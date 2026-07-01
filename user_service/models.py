from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from .validators import validar_cpf
import uuid
from django.utils import timezone
from easyaudit.models import CRUDEvent
from django.contrib.contenttypes.models import ContentType
from .manager import UsuarioManager,SoftDeleteManager
from django.utils.translation import gettext_lazy as _



class CreatedAtMixin(models.Model):
    created_at = models.DateTimeField(
        _("Created at"),
        auto_now_add=True,
        editable=False
    )

    class Meta:
        abstract = True


class UpdatedAtMixin(models.Model):
    updated_at = models.DateTimeField(
        _("Updated at"),
        auto_now=True,
    )

    class Meta:
        abstract = True


class CreatedByMixin(models.Model):
    created_by = models.ForeignKey(
        'user_service.Usuario',
        verbose_name=_("Created by"),
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_%(app_label)s_%(class)s_set",
    )

    class Meta:
        abstract = True


class UpdatedByMixin(models.Model):
    updated_by = models.ForeignKey(
        'user_service.Usuario',
        verbose_name=_("Updated by"),
        on_delete=models.SET_NULL,
        null=True,
        related_name="updated_%(app_label)s_%(class)s_set",
    )

    class Meta:
        abstract = True


# ==========================================
# 3. MIXINS AGRUPADOS
# ==========================================
class TimeStampedModel(CreatedAtMixin, UpdatedAtMixin):
    class Meta:
        abstract = True


class UserTrackedModel(CreatedByMixin, UpdatedByMixin):
    class Meta:
        abstract = True


# ==========================================
# 4. BASES GENÉRICAS
# ==========================================
class UUIDModel(models.Model):
    uuid = models.UUIDField(
        unique=True,
        editable=False,
        default=uuid.uuid4
    )

    class Meta:
        abstract = True


class SoftDeleteModel(models.Model):
    is_deleted = models.BooleanField(default=False)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    def delete(self, *args, **kwargs):
        self.is_deleted = True
        self.save()

    class Meta:
        abstract = True


# ==========================================
# 5. MODELO USUÁRIO
# ==========================================

# ==========================================
# 6. MODELOS BASE
# ==========================================
class BaseModel(UUIDModel, TimeStampedModel, UserTrackedModel):
    class Meta:
        abstract = True


class BaseModelWithSoftDelete(BaseModel, SoftDeleteModel):
    class Meta:
        abstract = True

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


class PasswordResetRequest(BaseModelWithSoftDelete):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE
    )

    token = models.CharField(
        max_length=255,
        unique=True
    )


    used_at = models.DateTimeField(
        null=True,
        blank=True
    )

    def is_expired(self, hours_valid=2):
        expiration_time = self.created_at + timezone.timedelta(hours=hours_valid)
        return timezone.now() > expiration_time
