from celery import shared_task
from .mltask import mltask

@shared_task
def ml_celery_task(file_path):
    mltask(file_path)
    return "DONE"