# veiculos/models.py

import re
from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from contratos.models import Contrato
from django.apps import apps
from datetime import date

# ========== FUNÇÃO DE VALIDAÇÃO DE PLACA (DEFINIR ANTES DA CLASSE) ==========
def validar_placa_modelo(valor):
    """
    Validador personalizado para placas nos formatos:
    - Antigo: ABC-1234
    - Mercosul: ABC1D23 (3 letras, 1 número, 1 letra, 2 números)
    """
    # se o valor for vazio, não faz validação (campo pode ser opcional)
    if not valor:
        return
    
    placa = valor.upper().strip()
    placa_sem_hifen = placa.replace("-", "")
    
    # Formato antigo: ABC-1234
    padrao_antigo = re.compile(r'^[A-Z]{3}-\d{4}$')
    # Formato Mercosul: AAA1A11
    padrao_mercosul = re.compile(r'^[A-Z]{3}\d[A-Z]\d{2}$')
    
    if padrao_antigo.match(placa):
        return
    elif padrao_mercosul.match(placa_sem_hifen):
        return
    else:
        raise ValidationError(
            f'Placa "{valor}" inválida. '
            f'Use o formato ABC-1234 (padrão antigo) ou ABC1D23 (Mercosul)'
        )


class Veiculo(models.Model):
    TIPO_VEICULO_CHOICES = [
            ("Carro", "Carro"),
            ("Caminhao", "Caminhão"),
            ("Utilitario", "Utilitário"),
            ("Equipamento", "Equipamento"),
            ("Implemento", "Implemento"),
            ("Veiculo", "Veículo"),  # Adicionado (singular)
            ("Veiculos", "Veículos"),  # Adicionado (plural)
            ("Van", "Van"),
            ("Onibus", "Ônibus"),
            ("Reboque", "Reboque"),
            ("Caminhonete", "Caminhonete"),
    ]

    COMBUSTIVEL_CHOICES = [
        ("Flex", "Flex"),
        ("Gasolina", "Gasolina"),
        ("Diesel", "Diesel"),
        ("Diesel S10", "Diesel S10"),
        ("Etanol", "Etanol"),
        ("Eletrico", "Elétrico"),
        ("Hibrido", "Híbrido"),
        ("N/A", "N/A"),  # Adicionado
        ("Alcool/Gasolina", "Álcool/Gasolina"),  # Adicionado
    ]

    CATEGORIA_CHOICES = [
        ("Leve", "Leve"),
        ("Medio", "Médio"),
        ("Pesado", "Pesado"),
        ("Equipamento", "Equipamento"),
        ("Implemento", "Implemento"),
        ("VAN", "VAN"),  # Adicionado
        ("Agricola", "Agrícola"),  # Adicionado
        ("Micro-Ônibus", "Micro-Ônibus"),  # Adicionado
        ("Onibus", "Ônibus"),  # Adicionado
        ("Caminhão Basculante", "Caminhão Basculante"),
        ("Caminhão de Transporte", "Caminhão de Transporte"),
        ("Caminhão Pipa", "Caminhão Pipa"),
        ("Caminhão Lubrificante", "Caminhão Lubrificante"),
        ("Caminhonete", "Caminhonete"),  # Adicionado
        ("Caminhão Comboio", "Caminhão Comboio"),  # Adicionado
        ("Caminhao Madeireiro", "Caminhão Madeireiro"),  # Adicionado
        ("Caminhão Munk", "Caminhão Munk"),  # Adicionado
        ("Trator de Esteira", "Trator de Esteira"),  # Adicionado
        ("Prancha", "Prancha"),  # Adicionado
        ("Rolo Compressor", "Rolo Compressor"),  # Adicionado
        ("Rolo Compactador", "Rolo Compactador"),  # Adicionado
        ("Veículo de Apoio", "Veículo de Apoio"),
        ("Reboque", "Reboque"),  # Adicionado
        ("Carreta","Carreta"),
        ("Grupo Gerador", "Grupo Gerador"),
        ("Escavadeira Hidráulica", "Escavadeira Hidráulica"),
        ("Escavadeira Anfíbia", "Escavadeira Anfíbia"),
        ("Motoniveladora", "Motoniveladora"),
        ("Pá Mecânica", "Pá Mecânica"),
        ("Outros", "Outros"),
        
    ]

    TIPO_PROPRIEDADE_CHOICES = [
        ("Proprio", "Próprio"),
        ("Locado", "Locado"),  # Adicionado (com L maiúsculo)
        ("Comodato", "Comodato"),
        ("Arrendado", "Arrendado"),
        ("LOCADO", "LOCADO"),  # Adicionado (maiúsculo)
    ]

    STATUS_CHOICES = [
        ("Disponivel", "Disponível"),
        ("EmTransito", "Em Trânsito"),
        ("Manutencao", "Manutenção"),
        ("Reservado", "Reservado"),
        ("Inativo", "Inativo"),
    ]

    CIDADE_CHOICES = [
        ("Curitiba", "Curitiba"),
        ("São Paulo", "São Paulo"),
        ("Rio de Janeiro", "Rio de Janeiro"),
        ("Outros", "Outros"),
    ]

    # Origem dos dados
    ORIGEM_CHOICES = [
        ("MANUAL", "Cadastro Manual"),
        ("PROTHEUS", "Importado do Protheus"),
        ("IMPORTACAO", "Importação por Planilha"),
    ]

    
    # DADOS PRINCIPAIS
    _importando = False

    
    placa = models.CharField(
    max_length=50,  
    null=True,
    blank=True
    )
    
    renavam = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        unique=False,
        validators=[]
    )

    identificador_externo = models.CharField(max_length=100, blank=True, null=True)
    marca = models.CharField(max_length=100)
    modelo = models.CharField(max_length=100)
    ano = models.IntegerField()
    cor = models.CharField(max_length=50, blank=True)

    contrato = models.ForeignKey(Contrato, on_delete=models.SET_NULL, null=True, blank=True)

    tag_interna = models.CharField(max_length=50, blank=True, null=True, unique=True)
    tag_cliente = models.CharField(max_length=50, blank=True, null=True)

    tipo = models.CharField(max_length=50, choices=TIPO_VEICULO_CHOICES)
    categoria = models.CharField(max_length=100, choices=CATEGORIA_CHOICES)
    combustivel = models.CharField(max_length=50, choices=COMBUSTIVEL_CHOICES)

    km_atual = models.PositiveIntegerField(default=0)
    km_anterior = models.PositiveIntegerField(default=0)

    horimetro_atual = models.PositiveIntegerField(default=0)
    horimetro_anterior = models.PositiveIntegerField(default=0)

    tipo_propriedade = models.CharField(
        max_length=40, choices=TIPO_PROPRIEDADE_CHOICES, default="Proprio"
    )

    status = models.CharField(
        max_length=40, choices=STATUS_CHOICES, default="Disponivel"
    )

    # ------------------------------------------------
    # DOCUMENTAÇÃO
    # ------------------------------------------------
    ipva_vencimento = models.DateField(blank=True, null=True)
    licenciamento_vencimento = models.DateField(blank=True, null=True)
    seguro = models.BooleanField(default=False)
    seguro_validade = models.DateField(blank=True, null=True)
    apolice_numero = models.CharField(max_length=50, blank=True, null=True)

    observacoes = models.TextField(blank=True, null=True)
    ativo = models.BooleanField(default=True)
    
    # Origem dos dados
    origem = models.CharField(
        max_length=20,
        choices=ORIGEM_CHOICES,
        default='MANUAL',
        blank=True,
        null=True
    )
    
    # Campos de auditoria
    criado_em = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    atualizado_em = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['tag_interna'], name='unique_veiculo_tag_interna'),
        ]
        ordering = ['placa']

    def __str__(self):
        return f"{self.placa or 'SEM PLACA'} - {self.modelo}"


    # Validações personalizadas
    def clean(self):

        tipos_veiculo = [
            "Carro", "Caminhao", "Utilitario", "Van",
            "Onibus", "Caminhonete", "Veiculo", "Veiculos"
        ]

        # -------------------------
        # NORMALIZAÇÃO INICIAL
        # -------------------------
        if self.placa:
            self.placa = str(self.placa).strip()
            if self.placa.lower() in ["nan", "none", "n/a", ""]:
                self.placa = None

        if self.renavam:
            self.renavam = ''.join(filter(str.isdigit, str(self.renavam)))

        if self.tipo in ["Equipamento", "Implemento"]:
            self.km_atual = 0
        else:
            self.horimetro_atual = 0    

        # -------------------------
        # VALIDAÇÃO DE PLACA (CONDICIONAL)
        # -------------------------
        if self.tipo in tipos_veiculo:
            if self.placa:
                placa_limpa = self.placa.upper()
                placa_sem_hifen = placa_limpa.replace("-", "")

                padrao_antigo = re.compile(r'^[A-Z]{3}-\d{4}$')
                padrao_mercosul = re.compile(r'^[A-Z]{3}\d[A-Z]\d{2}$')

                if not (padrao_antigo.match(placa_limpa) or padrao_mercosul.match(placa_sem_hifen)):
                    raise ValidationError({
                        'placa': 'Placa inválida para veículo. Use ABC-1234 ou ABC1D23'
                    })

                # normalização padrão
                if padrao_mercosul.match(placa_sem_hifen):
                    self.placa = placa_sem_hifen
                else:
                    self.placa = placa_limpa
        else:
            # Equipamentos → aceita qualquer valor
            if self.placa:
                self.placa = str(self.placa).strip()

        # -------------------------
        # RENAVAM ÚNICO (SE EXISTIR)
        # -------------------------
        if self.renavam and not getattr(self, "_importando", False):
            if Veiculo.objects.filter(renavam=self.renavam).exclude(id=self.id).exists():
                raise ValidationError({'renavam': f'Já existe veículo com este renavam {self.renavam}'})

        # -------------------------
        # VALIDAÇÕES GERAIS
        # -------------------------
        ano_atual = date.today().year

        if self.ano and (self.ano < 1900 or self.ano > ano_atual + 1):
            raise ValidationError({'ano': f'Ano deve estar entre 1900 e {ano_atual + 1}'})

        if self.km_atual < 0:
            raise ValidationError({'km_atual': 'KM não pode ser negativo'})


    def save(self, *args, **kwargs):
        tipos_veiculo = [
            "Carro", "Caminhao", "Utilitario", "Van",
            "Onibus", "Caminhonete", "Veiculo", "Veiculos"
        ]

        # -------------------------
        # NORMALIZAÇÃO SEGURA
        # -------------------------
        if self.placa:
            self.placa = str(self.placa).strip()
            if self.placa.lower() in ["nan", "none", "n/a", ""]:
                self.placa = None

        if self.renavam:
            self.renavam = ''.join(filter(str.isdigit, str(self.renavam)))

        if self.tag_interna:
            self.tag_interna = self.tag_interna.upper().strip().replace(" ", "")

        # -------------------------
        # FORMATAÇÃO DE PLACA (SÓ VEÍCULO)
        # -------------------------
        if self.tipo in tipos_veiculo and self.placa:
            placa_limpa = self.placa.upper()
            placa_sem_hifen = placa_limpa.replace("-", "")

            if re.match(r'^[A-Z]{3}\d[A-Z]\d{2}$', placa_sem_hifen):
                self.placa = placa_sem_hifen
            elif re.match(r'^[A-Z]{3}-\d{4}$', placa_limpa):
                self.placa = placa_limpa
            elif re.match(r'^[A-Z]{3}\d{4}$', placa_limpa):
                self.placa = f"{placa_limpa[:3]}-{placa_limpa[3:]}"

        # -------------------------
        # VALIDAÇÃO FINAL
        # -------------------------
        self.full_clean()

        super().save(*args, **kwargs)
    

    @property
    def placa_formatada(self):
        """Retorna placa formatada para exibição"""
        if not self.placa:
            return ""
        
        # Se for formato Mercosul (AAA1A11), exibe com hífen
        if re.match(r'^[A-Z]{3}\d[A-Z]\d{2}$', self.placa):
            return f"{self.placa[:3]}-{self.placa[3:]}"
        return self.placa
    
    @property
    def renavam_formatado(self):
        """Retorna renavam formatado"""
        if self.renavam and len(self.renavam) == 11:
            return f"{self.renavam[:4]}.{self.renavam[4:8]}.{self.renavam[8:]}"
        return self.renavam
    
    @property
    def km_anterior_formatado(self):
        """Retorna KM anterior formatado"""
        return f"{self.km_anterior:,}".replace(",", ".")
    
    @property
    def km_atual_formatado(self):
        """Retorna KM atual formatado"""
        return f"{self.km_atual:,}".replace(",", ".")
    
    @property
    def status_display(self):
        """Retorna status com ícone"""
        status_icons = {
            "Disponivel": "✅ Disponível",
            "EmTransito": "🚚 Em Trânsito",
            "Manutencao": "🔧 Manutenção",
            "Reservado": "📅 Reservado",
        }
        return status_icons.get(self.status, self.status)
    
    @property
    def status_color(self):
        """Retorna cor do status"""
        colors = {
            "Disponivel": "green",
            "EmTransito": "blue",
            "Manutencao": "orange",
            "Reservado": "purple",
        }
        return colors.get(self.status, "gray")
    
    @property
    def solicitacao_ativa(self):
        """Retorna solicitação ativa do veículo"""
        SolicitacaoVeiculo = apps.get_model("solicitacoes", "SolicitacaoVeiculo")
        return SolicitacaoVeiculo.objects.filter(
            veiculo=self,
            status__in=[
                "PENDENTE",
                "AGUARDANDO_CHECKLIST",
                "AGUARDANDO_SAIDA_PORTARIA",
                "EM_TRANSITO",
                "AGUARDANDO_CHECKLIST_RETORNO",
            ]
        ).order_by("-id").first()


class HistoricoKM(models.Model):
    veiculo = models.ForeignKey(Veiculo, on_delete=models.CASCADE, related_name='historico_km')
    km_anterior = models.PositiveIntegerField()
    km_novo = models.PositiveIntegerField()
    data_registro = models.DateTimeField(auto_now_add=True)
    origem = models.CharField(max_length=50, choices=[
        ('RETORNO_PORTARIA', 'Retorno Portaria'),
        ('AJUSTE_MANUAL', 'Ajuste Manual'),
        ('IMPORTACAO', 'Importação de Dados'),
    ])

    class Meta:
        ordering = ['-data_registro']

    def __str__(self):
        return f"{self.veiculo} - {self.km_anterior} → {self.km_novo}"

    def clean(self):
        """Validações do histórico KM"""
        if self.km_novo < self.km_anterior:
            raise ValidationError('KM novo não pode ser menor que KM anterior')