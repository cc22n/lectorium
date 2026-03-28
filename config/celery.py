"""
Celery configuration for LectoriumMVP.
Maneja transiciones automáticas de fase y tareas programadas.
"""

import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("lectorium")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
