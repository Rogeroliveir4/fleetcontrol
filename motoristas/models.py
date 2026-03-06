from django.db import models
from django.contrib.auth.models import User
from contratos.models import Contrato
from datetime import date

class Motorista(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    nome = models.CharField(max_length=255, blank=True, null=True)
    cpf = models.CharField(max_length=14,blank=True, null=True)
    telefone = models.CharField(max_length=20,blank=True, null=True)
    cnh_numero = models.CharField(max_length=20,blank=True, null=True)
    cnh_categoria = models.CharField(max_length=3,blank=True, null=True)
    cnh_vencimento = models.DateField(blank=True, null=True)
    email = models.CharField(max_length=20,blank=True, null=True)
    matricula = models.CharField(max_length=50)
    endereco = models.TextField(blank=True, null=True)
    cidade = models.CharField(max_length=100)
    estado = models.CharField(max_length=100, null=True, blank=True)
    contrato = models.ForeignKey(Contrato, on_delete=models.SET_NULL, null=True, blank=True)
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return self.nome
    
    @property
    def dias_para_vencimento(self):
        """Calcula os dias restantes para o vencimento da CNH"""
        if self.cnh_vencimento:
            hoje = date.today()
            # Calcular diferença em dias
            diferenca = self.cnh_vencimento - hoje
            return diferenca.days
        return None
    
    @property
    def status_cnh(self):
        """Retorna o status da CNH baseado nos dias para vencimento"""
        if not self.cnh_vencimento or self.dias_para_vencimento is None:
            return 'sem_info'
        
        if self.dias_para_vencimento <= 0:
            return 'vencida'
        elif self.dias_para_vencimento <= 30:
            return 'critico'
        elif self.dias_para_vencimento <= 60:
            return 'atencao'
        else:
            return 'ok'
    
    @property
    def status_cor(self):
        """Retorna a cor baseada no status da CNH"""
        status = self.status_cnh
        cores = {
            'vencida': 'red-600',
            'critico': 'red-500', 
            'atencao': 'amber-500',
            'ok': 'emerald-500',
            'sem_info': 'gray-500'
        }
        return cores.get(status, 'gray-500')
    
    @property
    def status_texto(self):
        """Retorna o texto do status da CNH"""
        status = self.status_cnh
        textos = {
            'vencida': 'VENCIDA',
            'critico': 'Crítico',
            'atencao': 'Atenção',
            'ok': 'OK',
            'sem_info': 'Sem data'
        }
        return textos.get(status, 'Sem data')