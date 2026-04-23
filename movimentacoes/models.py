# movimentacoes/models.py - VERSÃO CORRIGIDA E ORGANIZADA
from django.db import models
from veiculos.models import Veiculo
from motoristas.models import Motorista
from contratos.models import Contrato
from django.contrib.auth.models import User
from solicitacoes.models import SolicitacaoVeiculo

class Movimentacao(models.Model):
    STATUS_CHOICES = (
        ("aguardando_checklist_saida", "Aguardando Checklist de Saída"),
        ("aguardando_saida_portaria", "Aguardando Saída da Portaria"),
        ("em_andamento", "Em Andamento"),
        ("aguardando_checklist_retorno", "Aguardando Checklist de Retorno"),
        ("aguardando_retorno_portaria", "Aguardando Retorno da Portaria"),
        ("divergencia_km", "Divergência de KM"),
        ("finalizado", "Finalizado"),
    )

    ORIGEM_CHOICES = (
        ("SISTEMA", "Gerada pelo sistema"),
        ("MANUAL", "Criada manualmente"),
    )

    # RELACIONAMENTOS
    solicitacao = models.ForeignKey(
        SolicitacaoVeiculo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movimentacoes"
    )
    
    veiculo = models.ForeignKey(Veiculo, on_delete=models.CASCADE)
    motorista = models.ForeignKey(Motorista, on_delete=models.CASCADE)
    
    # CAMPOS GERAIS
    origem = models.CharField(
        max_length=20,
        choices=ORIGEM_CHOICES,
        default="SISTEMA",
        db_index=True
    )
    
    destino = models.CharField(max_length=255)
    finalidade = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=40, choices=STATUS_CHOICES)
    
    # DATAS E QUILOMETRAGEM
    km_saida = models.BigIntegerField(null=True, blank=True)
    km_retorno = models.BigIntegerField(null=True, blank=True)
    data_saida = models.DateTimeField(auto_now_add=True)
    data_retorno = models.DateTimeField(null=True, blank=True)
    distancia_percorrida = models.BigIntegerField(null=True, blank=True)
    
    # OBSERVAÇÕES SAÍDA E RETORNO
    observacao = models.TextField(blank=True)  # Observações gerais
    observacao_portaria = models.TextField(
        blank=True,
        null=True,
        verbose_name="Observações da portaria (saída)"
    )
    # RETORNO DA PORTARIA
    observacao_portaria_retorno = models.TextField( 
    blank=True,
    null=True,
    verbose_name="Observações da portaria (retorno)"
)
    
    # PORTEIROS
    porteiro_saida = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movimentacoes_porteiro_saida"
    )
    porteiro_saida_nome = models.CharField(max_length=120, null=True, blank=True)
    
    porteiro_retorno = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movimentacoes_porteiro_retorno"
    )
    porteiro_retorno_nome = models.CharField(max_length=120, null=True, blank=True)
    
    # EQUIPAMENTOS ESPECIAIS (SAÍDA)
    com_cacamba = models.BooleanField(
        default=False,
        verbose_name="Veículo com caçamba",
        help_text="Marque se o veículo saiu com caçamba carregada"
    )
    cacamba_descricao = models.TextField(
        blank=True,
        null=True,
        verbose_name="Descrição do material na caçamba"
    )
    
    com_prancha = models.BooleanField(
        default=False,
        verbose_name="Veículo com prancha",
        help_text="Marque se o veículo saiu com máquina na prancha"
    )
    prancha_descricao = models.TextField(
        blank=True,
        null=True,
        verbose_name="Descrição da máquina na prancha"
    )
    
    # === FOTOS DA SAÍDA (PORTARIA) ===
    foto_portaria_geral = models.ImageField(
        upload_to='portaria/saida/geral/%Y/%m/%d/',
        blank=True,
        null=True,
        verbose_name="Foto geral do veículo (saída)"
    )
    
    foto_portaria_painel = models.ImageField(
        upload_to='portaria/saida/painel/%Y/%m/%d/',
        blank=True,
        null=True,
        verbose_name="Foto do painel/odômetro (saída)"
    )
    
    foto_portaria_avaria = models.ImageField(
        upload_to='portaria/saida/avarias/%Y/%m/%d/',
        blank=True,
        null=True,
        verbose_name="Foto de avarias (saída)"
    )
    
    foto_portaria_equipamento = models.ImageField(
        upload_to='portaria/saida/equipamento/%Y/%m/%d/',
        blank=True,
        null=True,
        verbose_name="Foto do equipamento (saída)"
    )


    # ITENS NO VEÍCULO (SAÍDA)
    com_malas = models.BooleanField(
        default=False,
        verbose_name="Veículo com malas/maletas",
        help_text="Marque se o veículo saiu com malas ou maletas"
    )
    malas_descricao = models.TextField(
        blank=True,
        null=True,
        verbose_name="Descrição das malas/itens"
    )

    com_outros_itens = models.BooleanField(
        default=False,
        verbose_name="Veículo com outros itens",
        help_text="Marque se o veículo saiu com outros itens"
    )
    outros_itens_descricao = models.TextField(
        blank=True,
        null=True,
        verbose_name="Descrição de outros itens"
    )

    # FOTO DO INTERIOR/PORTA-MALAS (SAÍDA)
    foto_portaria_interior = models.ImageField(
        upload_to='portaria/saida/interior/%Y/%m/%d/',
        blank=True,
        null=True,
        verbose_name="Foto do interior/porta-malas (saída)"
    )
    
    # === FOTOS DO RETORNO (PORTARIA) - CAMPOS ESPECÍFICOS ===
    foto_retorno_geral = models.ImageField(
        upload_to='portaria/retorno/geral/%Y/%m/%d/',
        blank=True,
        null=True,
        verbose_name="Foto geral do veículo (retorno)"
    )
    
    foto_retorno_painel = models.ImageField(
        upload_to='portaria/retorno/painel/%Y/%m/%d/',
        blank=True,
        null=True,
        verbose_name="Foto do painel/odômetro (retorno)"
    )
    
    foto_retorno_avaria = models.ImageField(
        upload_to='portaria/retorno/avarias/%Y/%m/%d/',
        blank=True,
        null=True,
        verbose_name="Foto de avarias (retorno)"
    )
    
    foto_retorno_equipamento = models.ImageField(
        upload_to='portaria/retorno/equipamento/%Y/%m/%d/',
        blank=True,
        null=True,
        verbose_name="Foto do equipamento (retorno)"
    )
    
    # FOTOS ESPECÍFICAS DO RETORNO
    foto_retorno_cacamba = models.ImageField(
        upload_to='portaria/retorno/cacamba/%Y/%m/%d/',
        blank=True,
        null=True,
        verbose_name="Foto da caçamba (retorno)",
        help_text="Foto da caçamba no retorno"
    )
    
    foto_retorno_prancha = models.ImageField(
        upload_to='portaria/retorno/prancha/%Y/%m/%d/',
        blank=True,
        null=True,
        verbose_name="Foto da prancha (retorno)",
        help_text="Foto da máquina na prancha no retorno"
    )
    
    foto_retorno_porta_malas = models.ImageField(
        upload_to='portaria/retorno/porta_malas/%Y/%m/%d/',
        blank=True,
        null=True,
        verbose_name="Foto do porta-malas (retorno)",
        help_text="Foto do porta-malas no retorno"
    )
    
    foto_retorno_combustivel = models.ImageField(
        upload_to='portaria/retorno/combustivel/%Y/%m/%d/',
        blank=True,
        null=True,
        verbose_name="Foto do marcador de combustível (retorno)"
    )
    
    # CAMPOS DE COMPATIBILIDADE
    contrato = models.ForeignKey(
        Contrato,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Contrato vinculado"
    )

    def __str__(self):
        return f"{self.veiculo.placa} - {self.motorista.nome} ({self.status})"

    @property
    def com_equipamento_especial(self):
        """Propriedade para verificar se há equipamento especial"""
        return self.com_cacamba or self.com_prancha
    
    @property
    def equipamento_descricao(self):
        """Propriedade para obter descrição consolidada do equipamento"""
        descricoes = []
        if self.com_cacamba and self.cacamba_descricao:
            descricoes.append(f"Caçamba: {self.cacamba_descricao}")
        if self.com_prancha and self.prancha_descricao:
            descricoes.append(f"Prancha: {self.prancha_descricao}")
        return "; ".join(descricoes) if descricoes else None
    
    @property
    def em_andamento(self):
        """Propriedade para verificar se a movimentação está em andamento"""
        return self.data_retorno is None
    
    @property
    def tempo_viagem(self):
        """Calcula o tempo total da viagem"""
        if self.data_retorno:
            return self.data_retorno - self.data_saida
        return None
    
    @property
    def has_fotos_saida(self):
        """Verifica se há fotos da saída"""
        return any([
            self.foto_portaria_geral,
            self.foto_portaria_painel,
            self.foto_portaria_avaria,
            self.foto_portaria_equipamento
        ])
    
    @property
    def has_fotos_retorno(self):
        """Verifica se há fotos do retorno"""
        return any([
            self.foto_retorno_geral,
            self.foto_retorno_painel,
            self.foto_retorno_avaria,
            self.foto_retorno_equipamento,
            self.foto_retorno_cacamba,
            self.foto_retorno_prancha,
            self.foto_retorno_porta_malas,
            self.foto_retorno_combustivel
        ])
    
    @property
    def todas_fotos_saida(self):
        """Retorna um dict com todas as fotos da saída"""
        return {
            'geral': self.foto_portaria_geral,
            'painel': self.foto_portaria_painel,
            'avaria': self.foto_portaria_avaria,
            'equipamento': self.foto_portaria_equipamento
        }
    
    @property
    def todas_fotos_retorno(self):
        """Retorna um dict com todas as fotos do retorno"""
        return {
            'geral': self.foto_retorno_geral,
            'painel': self.foto_retorno_painel,
            'avaria': self.foto_retorno_avaria,
            'equipamento': self.foto_retorno_equipamento,
            'cacamba': self.foto_retorno_cacamba,
            'prancha': self.foto_retorno_prancha,
            'porta_malas': self.foto_retorno_porta_malas,
            'combustivel': self.foto_retorno_combustivel
        }


    @property
    def km_percorrido(self):
        """Calcula a quilometragem percorrida"""
        if self.km_retorno is not None and self.km_saida is not None:
            if self.km_retorno >= self.km_saida:
                return self.km_retorno - self.km_saida
            return 0
        return None
    
    
    @property
    def km_percorrido_formatado(self):
        """Retorna o km percorrido formatado"""
        km = self.km_percorrido
        if km is not None:
            return f"{km:,}".replace(",", ".")
        return "N/A"
    
    # OU, se preferir calcular automaticamente ao salvar:
    def save(self, *args, **kwargs):
        """Sobrescreve o save para calcular a distância percorrida"""
        if self.km_retorno is not None and self.km_saida is not None:
            if self.km_retorno >= self.km_saida:
                self.distancia_percorrida = self.km_retorno - self.km_saida
            else:
                self.distancia_percorrida = 0
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Movimentação"
        verbose_name_plural = "Movimentações"
        ordering = ['-data_saida']
        indexes = [
            models.Index(fields=['status', 'data_saida']),
            models.Index(fields=['veiculo', 'data_saida']),
            models.Index(fields=['motorista', 'data_saida']),
        ]


# Checklist de SAÍDA do Motorista
class ChecklistSaida(models.Model):
    movimentacao = models.OneToOneField(
        "Movimentacao", on_delete=models.CASCADE, related_name="checklist_saida"
    )

    # Verificações do checklist
    pneus_ok = models.BooleanField(default=True)
    luzes_ok = models.BooleanField(default=True)
    documentos_ok = models.BooleanField(default=True)
    equipamentos_ok = models.BooleanField(default=True)
    avarias = models.TextField(null=True, blank=True)

    # Fotos do checklist
    foto_painel = models.ImageField(upload_to="checklists/", null=True, blank=True)
    foto_frente = models.ImageField(upload_to="checklists/", null=True, blank=True)
    foto_traseira = models.ImageField(upload_to="checklists/", null=True, blank=True)
    foto_lado_esq = models.ImageField(upload_to="checklists/", null=True, blank=True)
    foto_lado_dir = models.ImageField(upload_to="checklists/", null=True, blank=True)
    foto_check_saida = models.ImageField(upload_to="checklists/", null=True, blank=True)

    # Observações
    observacoes = models.TextField(blank=True, null=True)
    data_registro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Checklist Saída #{self.movimentacao.id}"

    class Meta:
        verbose_name = "Checklist de Saída"
        verbose_name_plural = "Checklists de Saída"


# Checklist de RETORNO do Motorista
class ChecklistRetorno(models.Model):
    movimentacao = models.OneToOneField(
        "Movimentacao", 
        on_delete=models.CASCADE, 
        related_name="checklist_retorno"
    )

    # Verificações do checklist
    pneus_ok = models.BooleanField(default=True)
    luzes_ok = models.BooleanField(default=True)
    avarias_novas = models.TextField(null=True, blank=True)

    # Fotos do checklist retorno
    foto_painel = models.ImageField(upload_to="checklists/retorno/", null=True, blank=True)
    foto_frente = models.ImageField(upload_to="checklists/retorno/", null=True, blank=True)
    foto_traseira = models.ImageField(upload_to="checklists/retorno/", null=True, blank=True)
    foto_lado_esq = models.ImageField(upload_to="checklists/retorno/", null=True, blank=True)
    foto_lado_dir = models.ImageField(upload_to="checklists/retorno/", null=True, blank=True)
    foto_check_ret = models.ImageField(upload_to="checklists/", null=True, blank=True)

    # Observações
    observacoes = models.TextField(null=True, blank=True)
    data_registro = models.DateTimeField(auto_now_add=True)
    data_checklist = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    data_saida = models.DateTimeField(null=True, blank=True)
    
    # Porteiro que registrou a saída (para referência)
    porteiro_saida = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="saidas_registradas"
    )

    porteiro_saida_nome = models.CharField(
        max_length=120,
        null=True,
        blank=True
    )

    def __str__(self):
        return f"Checklist Retorno #{self.movimentacao.id}"

    class Meta:
        verbose_name = "Checklist de Retorno"
        verbose_name_plural = "Checklists de Retorno"


# Model do retorno da portaria (opcional, pode ser substituído pelos campos diretos em Movimentacao)
class RetornoPortaria(models.Model):
    movimentacao = models.OneToOneField(
        "Movimentacao", 
        on_delete=models.CASCADE, 
        related_name="retorno_portaria"
    )

    km_retorno = models.IntegerField()
    combustivel_retorno = models.IntegerField(null=True, blank=True)  # 0-100%
    observacao_portaria = models.TextField(null=True, blank=True)
    responsavel = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    data_registro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Retorno Portaria #{self.movimentacao.id} - {self.km_retorno}"

    class Meta:
        verbose_name = "Retorno da Portaria"
        verbose_name_plural = "Retornos da Portaria"


# Model para Movimentação de Terceiros
class MovimentacaoTerceiro(models.Model):
    STATUS_CHOICES = (
        ("ENTRADA", "Entrada"),
        ("SAIDA", "Saída"),
    )

    # Informações do veículo
    placa = models.CharField(max_length=10)
    tipo_veiculo = models.CharField(max_length=50)
    empresa = models.CharField(max_length=120)
    
    # Informações do motorista
    motorista_nome = models.CharField(max_length=120)
    documento = models.CharField(max_length=50, blank=True, null=True)
    
    # Descrições
    descricao_veiculo = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Descrição do veículo"
    )
    
    tags = models.CharField(
        max_length=120,
        blank=True,
        help_text="Ex: MANUTENCAO, VISITA, DESCARGA"
    )
    
    # Motivo e observações
    motivo_entrada = models.TextField(
        verbose_name="Motivo da entrada"
    )
    
    observacoes_entrada = models.TextField(
        blank=True,
        verbose_name="Observações da entrada",
        help_text="Observações feitas pelo porteiro no momento da entrada"
    )
    
    observacoes_saida = models.TextField(
        blank=True,
        verbose_name="Observações da saída",
        help_text="Observações feitas pelo porteiro no momento da saída"
    )
    
    # Status e datas
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="ENTRADA"
    )
    
    data_entrada = models.DateTimeField(auto_now_add=True)
    data_saida = models.DateTimeField(null=True, blank=True)
    
    # Porteiros responsáveis
    porteiro_entrada = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="terceiros_entrada"
    )
    porteiro_entrada_nome = models.CharField(max_length=120)
    
    porteiro_saida = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="terceiros_saida"
    )
    porteiro_saida_nome = models.CharField(max_length=120, blank=True)
    
    # Fotos
    foto_placa = models.ImageField(upload_to="terceiros/placa/")
    foto_veiculo = models.ImageField(upload_to="terceiros/veiculo/", blank=True, null=True)
    foto_motorista = models.ImageField(upload_to="terceiros/motorista/", blank=True, null=True)

    # Material/Equipamento
    foto_material = models.ImageField(
        upload_to='terceiros/material/%Y/%m/%d/',
        blank=True,
        null=True,
        verbose_name="Foto do material/equipamento"
    )
    
    descricao_material = models.TextField(
        blank=True,
        null=True,
        verbose_name="Descrição do material/equipamento"
    )

    # FOTOS DA SAÍDA
    foto_saida_veiculo = models.ImageField(
        upload_to='terceiros/saida/veiculo/%Y/%m/%d/',
        blank=True,
        null=True,
        verbose_name="Foto do veículo (saída)"
    )
    
    foto_saida_avaria = models.ImageField(
        upload_to='terceiros/saida/avarias/%Y/%m/%d/',
        blank=True,
        null=True,
        verbose_name="Foto de avaria (saída)"
    )
    
    foto_saida_extra = models.ImageField(
        upload_to='terceiros/saida/extra/%Y/%m/%d/',
        blank=True,
        null=True,
        verbose_name="Foto extra (saída)"
    )

    def __str__(self):
        return f"{self.placa} - {self.empresa} ({self.status})"
    
    # Propriedades para compatibilidade
    @property
    def observacoes(self):
        """Propriedade para manter compatibilidade com código existente"""
        return self.observacoes_entrada or ""
    
    @property
    def motivo(self):
        """Propriedade para manter compatibilidade"""
        return self.motivo_entrada or ""

    class Meta:
        verbose_name = "Movimentação de Terceiro"
        verbose_name_plural = "Movimentações de Terceiros"
        ordering = ['-data_entrada']