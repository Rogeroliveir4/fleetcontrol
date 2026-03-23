from django.contrib.auth.decorators import login_required  
from django.core.paginator import Paginator 
from motoristas.models import Motorista
from veiculos.models import Veiculo
from movimentacoes.models import Movimentacao
from django.shortcuts import render, redirect
from solicitacoes.models import SolicitacaoVeiculo
from django.utils import timezone
from datetime import datetime, timedelta
import xlsxwriter
from openpyxl.styles import Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import openpyxl
from django.db.models import Sum, Count, Q


@login_required
def dashboard(request):
    perfil = request.user.perfilusuario
    
    # Redireciona conforme o nível do usuário
    if perfil.nivel == "basico":
        return redirect("dashboard_motorista")
    elif perfil.nivel in ["gestor", "adm"]:
        return redirect("dashboard_gestor")
    else:
        # Nível desconhecido - redireciona para login ou página inicial
        return redirect("login")


# DASHBOARD DO GESTOR (COM DADOS REAIS DE SOLICITAÇÕES E MOVIMENTAÇÕES)
@login_required
def dashboard_gestor(request):
    """Dashboard do Gestor - Versão integrada com as mesmas estatísticas da tela de aprovações"""
    
    perfil = request.user.perfilusuario
    
    # ========== SOLICITAÇÕES DATA (MESMA LÓGICA DA TELA DE APROVAÇÕES) ==========
    if perfil.nivel == "adm":
        solicitacoes = SolicitacaoVeiculo.objects.select_related(
            "motorista", 
            "veiculo",
            "gestor_responsavel",
            "gestor_reprovador",
            "contrato"
        ).all()
    else:
        solicitacoes = SolicitacaoVeiculo.objects.select_related(
            "motorista", 
            "veiculo",
            "gestor_responsavel",
            "gestor_reprovador",
            "contrato"
        ).filter(contrato=perfil.contrato)
    
    # CONTAGEM PARA DASHBOARD (estatísticas principais)
    total_solicitacoes = solicitacoes.count()
    pendentes_count = solicitacoes.filter(status="PENDENTE").count()
    aprovadas_count = solicitacoes.filter(status="AGUARDANDO_SAIDA_PORTARIA").count()
    em_transito_count = solicitacoes.filter(status="EM_TRANSITO").count()
    finalizadas_count = solicitacoes.filter(status="FINALIZADA").count()
    reprovadas_count = solicitacoes.filter(status="REPROVADA").count()
    canceladas_count = solicitacoes.filter(status="CANCELADA").count()
    aguardando_saida_count = solicitacoes.filter(status="AGUARDANDO_SAIDA_PORTARIA").count()
    
    # Solicitações recentes (para lista)
    solicitacoes_recentes = solicitacoes.order_by("-data_criacao")[:5]
    
    # Calcular hoje e esta semana para solicitações
    hoje_data = timezone.now().date()
    hoje_solicitacoes = solicitacoes.filter(data_criacao__date=hoje_data).count()
    
    inicio_semana = hoje_data - timedelta(days=hoje_data.weekday())
    semana_solicitacoes = solicitacoes.filter(data_criacao__date__gte=inicio_semana).count()
    
    # ========== MOVIMENTAÇÕES DATA (dados reais de saída) ==========
    if perfil.nivel == "adm":
        movimentacoes = Movimentacao.objects.select_related(
            "veiculo", "motorista", "solicitacao"
        ).filter(data_saida__isnull=False)
    else:
        movimentacoes = Movimentacao.objects.select_related(
            "veiculo", "motorista", "solicitacao"
        ).filter(
            Q(contrato=perfil.contrato) | Q(solicitacao__contrato=perfil.contrato),
            data_saida__isnull=False
        ).distinct()
    
    # Movimentações counts
    mov_transito = movimentacoes.filter(data_retorno__isnull=True).count()
    mov_finalizadas = movimentacoes.filter(data_retorno__isnull=False).count()
    total_movimentacoes = movimentacoes.count()
    
    # Movimentações finalizadas hoje
    mov_finalizadas_hoje = movimentacoes.filter(data_retorno__date=hoje_data).count()
    
    # Movimentações no mês
    primeiro_dia_mes = hoje_data.replace(day=1)
    mov_total_mes = movimentacoes.filter(data_saida__date__gte=primeiro_dia_mes).count()
    
    # KM total no mês
    km_total_mes = movimentacoes.filter(
        data_retorno__date__gte=primeiro_dia_mes,
        data_retorno__isnull=False
    ).aggregate(total_km=Sum('distancia_percorrida'))['total_km'] or 0
    
    # Movimentações recentes (em andamento)
    movimentacoes_recentes = movimentacoes.filter(
        data_retorno__isnull=True
    ).order_by("-data_saida")[:5]
    
    # ========== TOPs das MOVIMENTAÇÕES reais ==========
    veiculos_top = movimentacoes.values(
        'veiculo__id',
        'veiculo__placa',
        'veiculo__modelo',
        'veiculo__marca'
    ).annotate(
        total_viagens=Count('id'),
        total_km=Sum('distancia_percorrida')
    ).filter(total_viagens__gt=0).order_by('-total_viagens')[:5]
    
    motoristas_top = movimentacoes.values(
        'motorista__id',
        'motorista__nome',
        'motorista__cpf'
    ).annotate(
        total_viagens=Count('id'),
        total_km=Sum('distancia_percorrida')
    ).filter(total_viagens__gt=0).order_by('-total_viagens')[:5]
    
    # Nome do contrato
    contrato_nome = perfil.contrato.nome if perfil.contrato and hasattr(perfil.contrato, 'nome') else None
    
    context = {
        # Solicitações data (mesmas estatísticas da tela de aprovações)
        "total_solicitacoes": total_solicitacoes,
        "pendentes": pendentes_count,
        "aprovadas": aprovadas_count,
        "em_transito": em_transito_count,
        "finalizadas": finalizadas_count,
        "reprovadas": reprovadas_count,
        "canceladas": canceladas_count,
        "aguardando_saida_count": aguardando_saida_count,
        "hoje": hoje_solicitacoes,
        "semana": semana_solicitacoes,
        "recentes": solicitacoes_recentes,
        
        # Movimentações data
        "mov_transito": mov_transito,
        "mov_finalizadas": mov_finalizadas,
        "total_movimentacoes": total_movimentacoes,
        "mov_finalizadas_hoje": mov_finalizadas_hoje,
        "mov_total_mes": mov_total_mes,
        "km_total_mes": km_total_mes,
        "movimentacoes_recentes": movimentacoes_recentes,
        
        # TOPs
        "veiculos_top": veiculos_top,
        "motoristas_top": motoristas_top,
        
        # Other
        "contrato": {"nome": contrato_nome} if contrato_nome else None,
    }
    
    return render(request, "core/dashboard_gestor.html", context)



# MESMA VISÃO DO DASHBOARD DO SOLICITANTE
@login_required
def dashboard_motorista(request):
    hoje = timezone.now().date()

    #  QUERY BASE — ESSA É A CHAVE
    qs = SolicitacaoVeiculo.objects.filter(
        solicitante=request.user
    )

    context = {
        "total": qs.count(),

        "pendentes": qs.filter(
            status="PENDENTE"
        ).count(),

        "aprovadas": qs.filter(
            status__in=[
                "AGUARDANDO_CHECKLIST",
                "AGUARDANDO_SAIDA_PORTARIA",
                "EM_TRANSITO",
                "AGUARDANDO_CHECKLIST_RETORNO",
            ]
        ).count(),

        "finalizadas": qs.filter(
            status="FINALIZADA"
        ).count(),


        "reprovadas": qs.filter(
            data_reprovacao__isnull=False
        ).count(),

        #  🆕 CANCELADAS (usa data_cancelamento)
        "canceladas": qs.filter(
            data_cancelamento__isnull=False
        ).count(),

        "hoje": qs.filter(
            data_criacao__date=hoje
        ).count(),

        "semana": qs.filter(
            data_criacao__date__gte=hoje - timedelta(days=7)
        ).count(),

        "mes": qs.filter(
            data_criacao__year=hoje.year,
            data_criacao__month=hoje.month
        ).count(),

        "recentes": qs.order_by("-data_criacao")[:5],
    }

    return render(request, "core/dashboard_solicitante.html", context)





def gestor_solicitacoes(request):

    if not request.user.is_authenticated:
        return redirect("login")

    perfil = request.user.perfilusuario
    if perfil.nivel != "gestor":
        return redirect("dashboard")

    contrato = perfil.contrato

    pendentes = SolicitacaoVeiculo.objects.filter(
        contrato=contrato,
        status="PENDENTE"
    ).select_related("motorista", "veiculo")

    return render(request, "gestor/solicitacoes_pendentes.html", {
        "pendentes": pendentes,
        "contrato": contrato,
    })



def aprovar_solicitacao(request, id):
    sol = SolicitacaoVeiculo.objects.get(id=id)

    perfil = request.user.perfilusuario
    if perfil.nivel != "gestor":
        return redirect("dashboard")

    sol.status = "APROVADA"
    sol.data_aprovacao = timezone.now()
    sol.gestor_responsavel = request.user
    sol.save()

    return redirect("gestor_solicitacoes")


def reprovar_solicitacao(request, id):
    sol = SolicitacaoVeiculo.objects.get(id=id)

    perfil = request.user.perfilusuario
    if perfil.nivel != "gestor":
        return redirect("dashboard")

    sol.status = "REPROVADA"
    sol.data_reprovacao = timezone.now()
    sol.gestor_responsavel = request.user
    sol.save()

    return redirect("gestor_solicitacoes")



