from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Motorista
from contas.models import PerfilUsuario

@receiver(post_save, sender=Motorista)
def setar_motorista_como_basico(sender, instance, created, **kwargs):
    if created and instance.user:
        perfil, criado = PerfilUsuario.objects.get_or_create(user=instance.user)
        perfil.nivel = "basico"
        perfil.save()
