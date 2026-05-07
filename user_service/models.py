from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from .validators import validar_cpf


class UsuarioManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('O email é obrigatório')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)

class Usuario(AbstractBaseUser, PermissionsMixin):
    TIPO_CHOICES = [('Motorista', 'Motorista'), ('Passageiro', 'Passageiro')]
    TIPO_CAMPUS = [
        ('Campus Natal-Central', 'Campus Natal-Central'),
        ('Campus Mossoró', 'Campus Mossoró'),
        # Adicione os outros campus aqui
    ]
    email = models.EmailField(unique=True)
    nome = models.CharField(max_length=255)
    telefone = models.CharField(max_length=15)
    cpf = models.CharField(max_length=14, unique=True, validators=[validar_cpf])
    tipo_usuario = models.CharField(max_length=50, choices=TIPO_CHOICES)
    tipo_campus = models.CharField(max_length=50, choices=TIPO_CAMPUS)
    foto = models.ImageField(upload_to='fotos_perfil/', null=True, blank=True)
    is_motorista = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UsuarioManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nome', 'cpf', 'telefone', 'tipo_usuario', 'tipo_campus']

    def __str__(self):
        return self.nome

