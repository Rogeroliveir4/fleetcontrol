from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from veiculos.models import Veiculo
from motoristas.models import Motorista
from solicitacoes.models import SolicitacaoVeiculo  
from contas.models import PerfilUsuario
from datetime import timedelta

# View para o dashboard do solicitante
@login_required
def dashboard_solicitante(request):
    hoje = timezone.now().date()
    inicio_semana = hoje - timedelta(days=7)
    inicio_mes = hoje.replace(day=1)

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

        #  REPROVADA NÃO É STATUS (usa data_reprovacao)
        "reprovadas": qs.filter(
            data_reprovacao__isnull=False
        ).count(),

        #   CANCELADAS (usa data_cancelamento)
        "canceladas": qs.filter(
            data_cancelamento__isnull=False
        ).count(),

        # Estatísticas temporais
        "hoje": qs.filter(
            data_criacao__date=hoje
        ).count(),

        "semana": qs.filter(
            data_criacao__date__gte=inicio_semana
        ).count(),

        "mes": qs.filter(
            data_criacao__date__gte=inicio_mes
        ).count(),

        # Últimas 5 solicitações
        "recentes": qs.order_by("-data_criacao")[:5],
        
        # Data atual para o header
        "data_atual": timezone.now(),
    }

    return render(request, "core/dashboard_solicitante.html", context)





# View para solicitar um veículo
@login_required
def solicitar_veiculo(request, veiculo_id):
    perfil = getattr(request.user, "perfilusuario", None)
    if not perfil:
        messages.error(request, "Perfil não encontrado.")
        return redirect("lista_movimentacoes")


    veiculo = get_object_or_404(Veiculo, id=veiculo_id)

    if perfil.nivel != "adm" and veiculo.contrato != perfil.contrato:
        messages.error(request, "Você não tem permissão para solicitar este veículo.")
        return redirect("dashboard_solicitante")

    motoristas = Motorista.objects.filter(contrato=veiculo.contrato)

    if request.method == "POST":
        motorista_id = request.POST.get("motorista")
        destino = request.POST.get("destino")
        previsao_retorno = request.POST.get("previsao_retorno")
        justificativa = request.POST.get("justificativa", "")

        if not motorista_id:
            messages.error(request, "Selecione um motorista.")
            return redirect("solicitar_veiculo", veiculo_id=veiculo.id)

        motorista = get_object_or_404(
            Motorista,
            id=motorista_id,
            contrato=veiculo.contrato
        )

        contrato = perfil.contrato or veiculo.contrato

        SolicitacaoVeiculo.objects.create(
            veiculo=veiculo,
            motorista=motorista,

            contrato=contrato,
            id_contrato=contrato.id if contrato else None,

            destino=destino,
            justificativa=justificativa,
            previsao_retorno=previsao_retorno,

            status="PENDENTE",
            data_criacao=timezone.now()
        )

        #messages.success(request, "Solicitação enviada ao gestor.")
        return redirect("dashboard_solicitante")

    return render(request, "solicitantes/solicitar.html", {
        "veiculo": veiculo,
        "motoristas": motoristas,
    })