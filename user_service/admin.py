from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from easyaudit.models import CRUDEvent
from .models import Usuario, Perfil

class UsuarioAudit(CRUDEvent):
    class Meta:
        proxy = True
        managed = False
        app_label = 'easyaudit'          # <-- ESSENCIAL
        verbose_name = 'Auditoria de Usuário'
        verbose_name_plural = 'Auditorias de Usuários'

class PerfilAudit(CRUDEvent):
    class Meta:
        proxy = True
        managed = False
        app_label = 'easyaudit'          # <-- ESSENCIAL
        verbose_name = 'Auditoria de Perfil'
        verbose_name_plural = 'Auditorias de Perfis'

@admin.register(UsuarioAudit)
class UsuarioAuditAdmin(admin.ModelAdmin):
    list_display = ('event_type', 'user', 'datetime', 'object_repr')
    list_filter = ('event_type', 'user', 'datetime')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        content_type = ContentType.objects.get_for_model(Usuario)
        return qs.filter(content_type=content_type)

@admin.register(PerfilAudit)
class PerfilAuditAdmin(admin.ModelAdmin):
    list_display = ('event_type', 'user', 'datetime', 'object_repr')
    list_filter = ('event_type', 'user', 'datetime')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        content_type = ContentType.objects.get_for_model(Perfil)
        return qs.filter(content_type=content_type)