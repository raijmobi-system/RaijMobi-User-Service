# meu_projeto/celery.py
import os
from celery import Celery

# Define o módulo de configurações padrão do Django para o Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

app = Celery('core')

# Lê as configurações do Celery a partir do settings.py usando o namespace 'CELERY'
app.config_from_object('django.conf:settings', namespace='CELERY')

# Descobre e carrega tarefas automaticamente nos arquivos tasks.py dos apps
app.autodiscover_tasks()