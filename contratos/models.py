from django.db import models

class Contrato(models.Model):
    nome = models.CharField(max_length=150)
    cliente = models.CharField(max_length=200, blank=True, null=True)
    localizacao = models.CharField(max_length=200, blank=True, null=True)
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nome} - {self.cliente}"