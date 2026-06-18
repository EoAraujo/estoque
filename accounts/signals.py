"""Signals: cria perfil automaticamente ao criar User."""
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import UserProfile


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def criar_ou_atualizar_perfil(sender, instance, created, **kwargs):
    UserProfile.objects.get_or_create(user=instance)
