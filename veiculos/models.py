from django.db import models
from contratos.models import Contrato
from django.apps import apps

class Veiculo(models.Model):
    TIPO_VEICULO_CHOICES = [
        ("Carro", "Carro"),
        ("Moto", "Moto"),
        ("Utilitario", "Utilitário"),
        ("Caminhao", "Caminhão"),
    ]

    COMBUSTIVEL_CHOICES = [
        ("Gasolina", "Gasolina"),
        ("Etanol", "Etanol"),
        ("Diesel", "Diesel"),
        ("Flex", "Flex"),
        ("GNV", "GNV"),
        ("Elétrico", "Elétrico"),
        ("Híbrido", "Híbrido"),
    ]

    CATEGORIA_CHOICES = [
        ("Leve", "Leve"),
        ("Pesado", "Pesado"),
        ("Passageiro", "Passageiro"),
        ("Carga", "Carga"),
        ("Onibus", "Ônibus"),
    ]

    TIPO_PROPRIEDADE_CHOICES = [
        ("Proprio", "Próprio"),
        ("Locado", "Locado"),
    ]

    STATUS_CHOICES = [
        ("Disponivel", "Disponível"),
        ("EmTransito", "Em Trânsito"),
        ("Manutencao", "Manutenção"),
        ("Reservado", "Reservado"),
    ]

    CIDADE_CHOICES = [
        ("Curitiba", "Curitiba"),
        ("São Paulo", "São Paulo"),
        ("Rio de Janeiro", "Rio de Janeiro"),
        ("Outros", "Outros"),
    ]

    # ------------------------------------------------
    # DADOS PRINCIPAIS
    # ------------------------------------------------
    placa = models.CharField(max_length=10, unique=True)
    renavam = models.CharField(max_length=20, blank=True, null=True)
    marca = models.CharField(max_length=100)
    modelo = models.CharField(max_length=100)
    ano = models.IntegerField()
    cor = models.CharField(max_length=50, blank=True)

    contrato = models.ForeignKey(Contrato, on_delete=models.SET_NULL, null=True, blank=True)

    tag_interna = models.CharField(max_length=50, blank=True, null=True)
    tag_cliente = models.CharField(max_length=50, blank=True, null=True)

    tipo = models.CharField(max_length=20, choices=TIPO_VEICULO_CHOICES)
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES)
    combustivel = models.CharField(max_length=20, choices=COMBUSTIVEL_CHOICES)

    km_atual = models.PositiveIntegerField(default=0)
    km_anterior = models.PositiveIntegerField(default=0)

    tipo_propriedade = models.CharField(
        max_length=20, choices=TIPO_PROPRIEDADE_CHOICES, default="Proprio"
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

    def __str__(self):
        return f"{self.placa} - {self.modelo}"


    @property
    def solicitacao_ativa(self):
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

    def __str__(self):
        return f"{self.veiculo} - {self.km_anterior} → {self.km_novo}"



