from django.db import models
from django.conf import settings
from django.contrib.auth.models import User  # Importação faltando
from contratos.models import Contrato


class PerfilUsuario(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    contrato = models.ForeignKey(Contrato, on_delete=models.SET_NULL, null=True, blank=True)
    nome = models.CharField(max_length=100, null=True, blank=True)
    
    # Nome exibido no sistema
    nome_exibicao = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="Nome exibido"
    )


    nivel = models.CharField(
        max_length=20,
        choices=[
            ("adm", "Administrador"),
            ("gestor", "Gestor"),
            ("portaria", "Portaria"),   
            ("basico", "Solicitante"),
        ],
        default="basico"
    )

    def __str__(self):
        return f"{self.nome_exibicao or self.user.username} ({self.nivel})"



class Contrato(models.Model):
    nome = models.CharField(max_length=150, unique=True)
    codigo = models.CharField(max_length=50, unique=True, blank=True, null=True)
    cliente = models.CharField(max_length=200, blank=True, null=True)
    ativo = models.BooleanField(default=True)

    data_inicio = models.DateField(blank=True, null=True)
    data_fim = models.DateField(blank=True, null=True)

    def __str__(self):
        return self.nome

