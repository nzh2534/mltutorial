from django.db import models
from django.dispatch import receiver
from .tasks import ml_celery_task
from django.db.models.signals import(
    post_save
)

# Create your models here.

class Document(models.Model):
    title = models.CharField(max_length=200)
    file = models.FileField(blank=True, null=True, default="")

@receiver(post_save, sender=Document)
def user_created_handler(sender, instance, *args, **kwargs):
    ml_celery_task.delay(str(instance.file.file))