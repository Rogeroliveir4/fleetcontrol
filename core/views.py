from django.shortcuts import render
from django.contrib.auth.decorators import login_required  
from django.core.paginator import Paginator 
from motoristas.models import Motorista
from veiculos.models import Veiculo
from movimentacoes.models import Movimentacao
from django.shortcuts import render, redirect
from solicitacoes.models import SolicitacaoVeiculo
from django.db.models import Q, Count
from django.utils import timezone
from datetime import datetime, timedelta
import xlsxwriter
from openpyxl.styles import Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import openpyxl


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


@login_required
def dashboard_gestor(request):
    perfil = request.user.perfilusuario
    
    # Verificar se tem permissão
    if perfil.nivel not in ["gestor", "adm"]:
        return redirect('dashboard')
    
    contrato = perfil.contrato
    
    # Base do queryset
    if perfil.nivel == "adm":
        base_queryset = SolicitacaoVeiculo.objects.all()
    else:
        base_queryset = SolicitacaoVeiculo.objects.filter(contrato=contrato)
    
    # Estatísticas principais
    stats = {
        'pendentes': base_queryset.filter(status="PENDENTE").count(),
        'aprovadas': base_queryset.filter(
            status__in=["AGUARDANDO_SAIDA_PORTARIA", "EM_TRANSITO", "FINALIZADA"]
        ).count(),
        'reprovadas': base_queryset.filter(status="REPROVADA").count(),
        'em_transito': base_queryset.filter(status="EM_TRANSITO").count(),
        'total': base_queryset.count(),
        'hoje': base_queryset.filter(data_criacao__date=timezone.now().date()).count(),
        'semana': base_queryset.filter(
            data_criacao__date__gte=timezone.now().date() - timedelta(days=7)
        ).count(),
    }
    
    # Solicitações recentes
    recentes = base_queryset.select_related(
        "motorista", "veiculo"
    ).order_by('-data_criacao')[:10]
    
    # Solicitações pendentes
    pendentes_list = base_queryset.filter(status="PENDENTE").select_related(
        "motorista", "veiculo"
    ).order_by('-data_criacao')[:5]
    
    # Veículos mais solicitados
    veiculos_top = base_queryset.values(
        'veiculo__placa', 
        'veiculo__modelo',
        'veiculo__marca'
    ).annotate(
        total=Count('id')
    ).order_by('-total')[:5]
    
    # Motoristas mais ativos
    motoristas_top = base_queryset.values(
        'motorista__nome',
        'motorista__cpf'
    ).annotate(
        total=Count('id')
    ).order_by('-total')[:5]
    
    return render(request, "core/dashboard_gestor.html", {
        'contrato': contrato,
        'pendentes': stats['pendentes'],
        'aprovadas': stats['aprovadas'],
        'reprovadas': stats['reprovadas'],
        'em_transito': stats['em_transito'],
        'total': stats['total'],
        'hoje': stats['hoje'],
        'semana': stats['semana'],
        'recentes': recentes,
        'pendentes_list': pendentes_list,
        'veiculos_top': veiculos_top,
        'motoristas_top': motoristas_top,
        'SolicitacaoVeiculo': SolicitacaoVeiculo,
        'perfil_usuario': perfil,
    })


# MESMA VISÃO DO DASHBOARD DO SOLICITANTE
@login_required
def dashboard_motorista(request):
    hoje = timezone.now().date()

    # 🔐 QUERY BASE — ESSA É A CHAVE
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



