from django.db import models
from django.contrib.auth.models import User
from contratos.models import Contrato
from datetime import date
from django.core.exceptions import ValidationError

class Motorista(models.Model):
    # Opções para origem dos dados
    ORIGEM_CHOICES = [
        ('MANUAL', 'Cadastro Manual'),
        ('PROTHEUS', 'Importado do Protheus'),
        ('IMPORTACAO', 'Importação por Planilha'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    nome = models.CharField(max_length=255, blank=True, null=True)
    cpf = models.CharField(max_length=14, blank=True, null=True, unique=True)  # 👈 UNIQUE
    telefone = models.CharField(max_length=20, blank=True, null=True)
    cnh_numero = models.CharField(max_length=20, blank=True, null=True)
    cnh_categoria = models.CharField(max_length=3, blank=True, null=True)
    cnh_vencimento = models.DateField(blank=True, null=True)
    email = models.CharField(max_length=20, blank=True, null=True)
    matricula = models.CharField(max_length=50, unique=True)  # 👈 UNIQUE
    endereco = models.TextField(blank=True, null=True)
    cidade = models.CharField(max_length=100)
    estado = models.CharField(max_length=100, null=True, blank=True)
    contrato = models.ForeignKey(Contrato, on_delete=models.SET_NULL, null=True, blank=True)
    ativo = models.BooleanField(default=True)
    origem = models.CharField(
        max_length=20,
        choices=ORIGEM_CHOICES,
        default='MANUAL',
        blank=True,
        null=True
    )
    criado_em = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    atualizado_em = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['cpf'], name='unique_motorista_cpf'),
            models.UniqueConstraint(fields=['matricula'], name='unique_motorista_matricula'),
        ]
        ordering = ['nome']

    def __str__(self):
        return f"{self.nome} - {self.matricula}" if self.nome else self.matricula
    
    def clean(self):
        """Validações antes de salvar"""
        # Validar CPF (apenas números e 11 dígitos)
        if self.cpf:
            cpf_limpo = self.cpf.replace(".", "").replace("-", "").replace("/", "")
            if not cpf_limpo.isdigit():
                raise ValidationError({'cpf': 'CPF deve conter apenas números.'})
            if len(cpf_limpo) != 11:
                raise ValidationError({'cpf': 'CPF deve ter 11 dígitos.'})
            # Atualizar CPF para o formato limpo
            self.cpf = cpf_limpo
        
        # Validar matrícula (apenas números)
        if self.matricula:
            matricula_limpa = ''.join(filter(str.isdigit, self.matricula))
            if not matricula_limpa:
                raise ValidationError({'matricula': 'Matrícula deve conter apenas números.'})
            if len(matricula_limpa) < 3:
                raise ValidationError({'matricula': 'Matrícula deve ter pelo menos 3 dígitos.'})
            self.matricula = matricula_limpa
        
        # Validar telefone (opcional)
        if self.telefone:
            telefone_limpo = ''.join(filter(str.isdigit, self.telefone))
            if len(telefone_limpo) < 10:
                raise ValidationError({'telefone': 'Telefone deve ter pelo menos 10 dígitos.'})
        
        # Validar nome (opcional)
        if self.nome and len(self.nome.strip()) < 3:
            raise ValidationError({'nome': 'Nome deve ter pelo menos 3 caracteres.'})
        
        # Validar CNH
        if self.cnh_numero:
            cnh_limpo = ''.join(filter(str.isdigit, self.cnh_numero))
            if len(cnh_limpo) < 9:
                raise ValidationError({'cnh_numero': 'CNH deve ter pelo menos 9 dígitos.'})
    
    def save(self, *args, **kwargs):
        # Limpar campos antes de salvar
        if self.cpf:
            self.cpf = self.cpf.replace(".", "").replace("-", "").replace("/", "")
        
        if self.matricula:
            self.matricula = ''.join(filter(str.isdigit, self.matricula))
        
        if self.nome:
            self.nome = self.nome.upper().strip()
        
        if self.cnh_categoria:
            self.cnh_categoria = self.cnh_categoria.upper().strip()
        
        if self.telefone:
            self.telefone = ''.join(filter(str.isdigit, self.telefone))
        
        if self.cnh_numero:
            self.cnh_numero = ''.join(filter(str.isdigit, self.cnh_numero))
        
        self.full_clean()  # Executar validações
        super().save(*args, **kwargs)
    
    @property
    def dias_para_vencimento(self):
        """Calcula os dias restantes para o vencimento da CNH"""
        if self.cnh_vencimento:
            hoje = date.today()
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
    
    @property
    def cpf_formatado(self):
        """Retorna CPF formatado com pontuação"""
        if self.cpf and len(self.cpf) == 11:
            return f"{self.cpf[:3]}.{self.cpf[3:6]}.{self.cpf[6:9]}-{self.cpf[9:]}"
        return self.cpf
    
    @property
    def telefone_formatado(self):
        """Retorna telefone formatado"""
        if self.telefone and len(self.telefone) == 11:
            return f"({self.telefone[:2]}) {self.telefone[2:7]}-{self.telefone[7:]}"
        elif self.telefone and len(self.telefone) == 10:
            return f"({self.telefone[:2]}) {self.telefone[2:6]}-{self.telefone[6:]}"
        return self.telefone