# Commonly used in Django projects to ensure that the Celery application instance (celery_app) is automatically imported when Django starts.
from .celery import app as celery_app

__all__ = ('celery_app',)