from django.contrib import admin

# Register your models here.
# usuarios/admin.py
from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from .models import UsuarioAudit, PerfilAudit
from .models import Usuario, Perfil   # seus modelos originais

class UsuarioAuditAdmin(admin.ModelAdmin):
    list_display = ('event_type', 'user', 'datetime', 'object_repr')
    list_filter = ('event_type', 'user', 'datetime')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        content_type = ContentType.objects.get_for_model(Usuario)
        return qs.filter(content_type=content_type)

class PerfilAuditAdmin(admin.ModelAdmin):
    list_display = ('event_type', 'user', 'datetime', 'object_repr')
    list_filter = ('event_type', 'user', 'datetime')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        content_type = ContentType.objects.get_for_model(Perfil)
        return qs.filter(content_type=content_type)

admin.site.register(UsuarioAudit, UsuarioAuditAdmin)
admin.site.register(PerfilAudit, PerfilAuditAdmin)