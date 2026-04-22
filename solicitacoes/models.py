from django.db import models
from veiculos.models import Veiculo
from motoristas.models import Motorista
from contratos.models import Contrato
from django.contrib.auth.models import User



class SolicitacaoVeiculo(models.Model):

    STATUS_CHOICES = [
        ("PENDENTE", "Pendente"),
        ("AGUARDANDO_CHECKLIST", "Aguardando Checklist"),
        ("AGUARDANDO_SAIDA_PORTARIA", "Aguardando Saída na Portaria"),
        ("EM_TRANSITO", "Em Trânsito"),
        ("REPROVADA", "Reprovada"),
        ("CANCELADA", "Cancelada"),
        ("AGUARDANDO_CHECKLIST_RETORNO", "Aguardando Checklist Retorno"),
        ("FINALIZADA", "Finalizada"),
    ]


    # AUDITORIA – SOLICITANTE
    solicitante = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="solicitacoes_criadas"
    )

    solicitante_nome = models.CharField(
        max_length=120,
        null=True,
        blank=True
    )     

    veiculo = models.ForeignKey(
        Veiculo,
        on_delete=models.CASCADE,
        related_name="solicitacoes"
    )

    motorista = models.ForeignKey(
        Motorista,
        on_delete=models.CASCADE,
        related_name="solicitacoes"
    )
    
    contrato = models.ForeignKey(
        Contrato,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    id_contrato = models.IntegerField(null=True, blank=True)

    tag_interna = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        db_index=True,  # Índice para busca rápida
        help_text="Código identificador interno da solicitação (ex: VA-950, TAG-123)"
    )

    destino = models.CharField(max_length=255)
    justificativa = models.TextField(blank=True, null=True)
    previsao_retorno = models.DateTimeField(null=True, blank=True)
    previsao_saida = models.DateTimeField(null=True, blank=True)

    status = models.CharField(
        max_length=40,
        choices=STATUS_CHOICES,
        default='PENDENTE'
    )

    # Datas do fluxo
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_aprovacao = models.DateTimeField(null=True, blank=True)
    data_reprovacao = models.DateTimeField(null=True, blank=True)
    data_saida = models.DateTimeField(null=True, blank=True)
    data_retorno = models.DateTimeField(null=True, blank=True)

    # Cancelamento da solicitação
    motivo_cancelamento = models.TextField(null=True, blank=True)
    data_cancelamento = models.DateTimeField(null=True, blank=True)


    # AUDITORIA – CANCELAMENTO
    cancelado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="solicitacoes_canceladas"
    )

    cancelado_por_nome = models.CharField(
        max_length=120,
        null=True,
        blank=True
    )

    

    # AUDITORIA – APROVAÇÃO
    ORIGEM_CHOICES = (
        ("SISTEMA", "Gerada pelo sistema"),
        ("MANUAL", "Criada manualmente"),
    )

    origem = models.CharField(
        max_length=20,
        choices=ORIGEM_CHOICES,
        default="SISTEMA",
        db_index=True
    )

    # FK do usuário que aprovou
    gestor_responsavel = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="solicitacoes_aprovadas"
    )

    # Nome congelado (snapshot da aprovação)
    gestor_responsavel_nome = models.CharField(
        max_length=120,
        null=True,
        blank=True
    )

    observacao_aprovacao = models.TextField(
    null=True,
    blank=True,
    help_text="Observações do gestor ao aprovar a solicitação"
    )

    # AUDITORIA – REPROVAÇÃO
    gestor_reprovador = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="solicitacoes_reprovadas"
    )

    gestor_reprovador_nome = models.CharField(
        max_length=120,
        null=True,
        blank=True
    )

    motivo_reprovacao = models.TextField(
    null=True,
    blank=True,
    help_text="Motivo informado pelo gestor ao reprovar a solicitação"
    )

    def __str__(self):
        return f"Solicitação #{self.id} - {self.veiculo} ({self.status})"


    @property
    def nome_cancelador(self):
        if self.cancelado_por_nome:
            return self.cancelado_por_nome
        if self.cancelado_por:
            return self.cancelado_por.get_full_name() or self.cancelado_por.username
        return "Usuário não identificado"



    # Propriedade para obter a movimentação ativa (aguardando checklist de retorno)
    @property
    def movimentacao_ativa(self):
        return self.movimentacoes.filter(
            status="aguardando_checklist_retorno"
        ).order_by("-id").first()


    def save(self, *args, **kwargs):
        #  Preenche automaticamente o nome do solicitante a partir do perfil
        if self.solicitante and not self.solicitante_nome:
            try:
                perfil = self.solicitante.perfilusuario
                # Prioridade: nome_exibicao > nome > username formatado
                if perfil.nome_exibicao:
                    self.solicitante_nome = perfil.nome_exibicao
                elif perfil.nome:
                    self.solicitante_nome = perfil.nome
                else:
                    # Fallback para username formatado
                    username = self.solicitante.username.split('@')[0]
                    self.solicitante_nome = username.replace('.', ' ').title()
            except Exception as e:
                # Se houver erro, usa fallback
                username = self.solicitante.username.split('@')[0]
                self.solicitante_nome = username.replace('.', ' ').title()
        
        #  Mesma lógica para gestor_responsavel
        if self.gestor_responsavel and not self.gestor_responsavel_nome:
            try:
                perfil = self.gestor_responsavel.perfilusuario
                if perfil.nome_exibicao:
                    self.gestor_responsavel_nome = perfil.nome_exibicao
                elif perfil.nome:
                    self.gestor_responsavel_nome = perfil.nome
                else:
                    username = self.gestor_responsavel.username.split('@')[0]
                    self.gestor_responsavel_nome = username.replace('.', ' ').title()
            except:
                username = self.gestor_responsavel.username.split('@')[0]
                self.gestor_responsavel_nome = username.replace('.', ' ').title()
        
        #  Mesma lógica para gestor_reprovador
        if self.gestor_reprovador and not self.gestor_reprovador_nome:
            try:
                perfil = self.gestor_reprovador.perfilusuario
                if perfil.nome_exibicao:
                    self.gestor_reprovador_nome = perfil.nome_exibicao
                elif perfil.nome:
                    self.gestor_reprovador_nome = perfil.nome
                else:
                    username = self.gestor_reprovador.username.split('@')[0]
                    self.gestor_reprovador_nome = username.replace('.', ' ').title()
            except:
                username = self.gestor_reprovador.username.split('@')[0]
                self.gestor_reprovador_nome = username.replace('.', ' ').title()
        
        super().save(*args, **kwargs)

