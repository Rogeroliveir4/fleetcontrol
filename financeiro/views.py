from django.shortcuts import render
from .models import IPVA, Licenciamento, Multa, Manutencao
from django.db.models import Sum, Q


def dashboard_financeiro(request):

    total_ipva = IPVA.objects.count()
    total_licenciamento = Licenciamento.objects.count()
    total_multas = Multa.objects.count()
    total_manutencoes = Manutencao.objects.count()

    valor_multas = Multa.objects.aggregate(total=Sum("valor"))["total"] or 0
    valor_manutencoes = Manutencao.objects.aggregate(total=Sum("valor"))["total"] or 0

    context = {
        "total_ipva": total_ipva,
        "total_licenciamento": total_licenciamento,
        "total_multas": total_multas,
        "total_manutencoes": total_manutencoes,
        "valor_multas": valor_multas,
        "valor_manutencoes": valor_manutencoes,
    }

    return render(request, "financeiro/dashboard.html", context)

# Views para listar cada tipo de despesa (IPVA, Licenciamento, Multas, Manutenções)
from django.shortcuts import render
from django.db.models import Q, Sum
from .models import IPVA


# LISTAGEM DE IPVA
from django.shortcuts import render
from django.db.models import Q, Sum
from .models import IPVA

# View para listar os IPVA
def lista_ipva(request):

    ipvas = IPVA.objects.select_related("veiculo").all()

    # busca
    search = request.GET.get("search")
    if search:
        ipvas = ipvas.filter(
            Q(veiculo__placa__icontains=search) |
            Q(veiculo__modelo__icontains=search) |
            Q(veiculo__marca__icontains=search)
        )

    # filtros de data
    inicio = request.GET.get("inicio")
    fim = request.GET.get("fim")

    if inicio:
        ipvas = ipvas.filter(data_vencimento__gte=inicio)

    if fim:
        ipvas = ipvas.filter(data_vencimento__lte=fim)

    # contadores
    ipvas_count = ipvas.count()

    pagos_count = ipvas.filter(status="pago").count()
    pendentes_count = ipvas.filter(status="pendente").count()

    total_pago = ipvas.filter(status="pago").aggregate(
        total=Sum("valor")
    )["total"] or 0

    total_pendente = ipvas.filter(status="pendente").aggregate(
        total=Sum("valor")
    )["total"] or 0

    context = {
        "ipvas": ipvas,   # ESSA VARIÁVEL É A QUE O TEMPLATE USA
        "ipvas_count": ipvas_count,
        "retornos_count": pendentes_count,
        "aprovadas_count": pagos_count,
        "reprovadas_count": total_pendente,
        "pendentes_count": total_pago,
    }

    return render(request, "financeiro/lista_ipva.html", context)


def lista_licenciamento(request):
    return render(request, "financeiro/lista_licenciamento.html")