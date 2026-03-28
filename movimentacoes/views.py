from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string
from django.core.paginator import Paginator
from veiculos.models import Veiculo
from motoristas.models import Motorista
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment
from django.db.models import Q
from django.contrib import messages
from .models import Movimentacao, ChecklistSaida, ChecklistRetorno, RetornoPortaria
from solicitacoes.models import SolicitacaoVeiculo
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import MovimentacaoTerceiro
from contratos.models import Contrato
from django.utils.timezone import localtime



# FUNÇÃO AUXILIAR PARA APLICAR FILTROS (REUTILIZÁVEL)
def aplicar_filtros_movimentacoes(request, queryset):
    status = request.GET.get("status", "")
        
    search = request.GET.get("search", "").strip()
    inicio = request.GET.get("inicio")
    fim = request.GET.get("fim")

    perfil = getattr(request.user, "perfilusuario", None)

    #  Restrição por contrato
    if perfil and perfil.nivel == "gestor" and perfil.contrato:
            queryset = queryset.filter(
                Q(contrato=perfil.contrato) |
                Q(contrato__isnull=True, solicitacao__contrato=perfil.contrato)
            )

    #  SEARCH
    if search:
        if "-" in search and search.upper().startswith("VA"):
            queryset = queryset.filter(veiculo__tag_interna__iexact=search)

        elif "-" in search and len(search) >= 7:
            queryset = queryset.filter(veiculo__placa__iexact=search)

        elif search.isdigit():
            queryset = queryset.filter(id=int(search))

        else:
            queryset = queryset.filter(
                Q(veiculo__placa__icontains=search) |
                Q(motorista__nome__icontains=search) |
                Q(veiculo__modelo__icontains=search) |
                Q(veiculo__marca__icontains=search) |
                Q(veiculo__tag_interna__icontains=search)
            )

    #  STATUS
    if status == "transito":
        queryset = queryset.filter(data_retorno__isnull=True)
    elif status == "finalizada":
        queryset = queryset.filter(data_retorno__isnull=False)

    #  DATA
    if inicio:
        queryset = queryset.filter(data_saida__date__gte=inicio)

    if fim:
        queryset = queryset.filter(data_saida__date__lte=fim)

    return queryset


# NOVA VIEW: Lista para portaria registrar retorno (movs em andamento)
def portaria_retorno_list(request):
    movimentacoes = Movimentacao.objects.filter(
        status="em_andamento"
    ).select_related(
        "veiculo", "motorista", "solicitacao"
    ).order_by("-data_saida")

    return render(request, "portaria/retorno_list.html", {
        "movimentacoes": movimentacoes
    })


# LISTA DE MOVIMENTAÇÕES COM FILTROS E PAGINAÇÃO
def lista_movimentacoes(request):
    status = request.GET.get("status", "transito")

    try:
        limite = int(request.GET.get("limite", 10))
        if limite not in [5, 10, 15, 20, 30]:
            limite = 10
    except:
        limite = 10

    search = request.GET.get("search", "").strip()
    inicio = request.GET.get("inicio")
    fim = request.GET.get("fim")

    # Query base
    movs = (
        Movimentacao.objects
        .select_related("veiculo", "motorista", "solicitacao", "solicitacao__contrato")
        .order_by("-data_saida")
    )


    #  FILTRO AUTOMÁTICO POR CONTRATO (GESTOR)
    perfil = getattr(request.user, "perfilusuario", None)

    if perfil and perfil.nivel == "gestor" and perfil.contrato:
        movs = movs.filter(
            Q(contrato=perfil.contrato) |
            Q(contrato__isnull=True, solicitacao__contrato=perfil.contrato)
        )

    # APLICAR FILTROS
    if search:
        search = search.strip()

        if "-" in search and search.upper().startswith("VA"):
            movs = movs.filter(veiculo__tag_interna__iexact=search)

        elif "-" in search and len(search) >= 7:
            movs = movs.filter(veiculo__placa__iexact=search)

        elif search.isdigit():
            movs = movs.filter(id=int(search))

        else:
            movs = movs.filter(
                Q(veiculo__placa__icontains=search) |
                Q(motorista__nome__icontains=search) |
                Q(veiculo__tag_interna__icontains=search)
        )

    if status == "transito":
        movs = movs.filter(data_retorno__isnull=True)
    elif status == "finalizada":
        movs = movs.filter(data_retorno__isnull=False)

    if inicio:
        movs = movs.filter(data_saida__date__gte=inicio)
    if fim:
        movs = movs.filter(data_saida__date__lte=fim)

    # Paginação
    paginator = Paginator(movs, limite)
    page = request.GET.get("page")
    movimentacoes = paginator.get_page(page)

    # Contadores (respeitando perfil)
    base_count = Movimentacao.objects.all()

    if perfil and perfil.nivel == "gestor" and perfil.contrato:
        base_count = base_count.filter(
            Q(contrato=perfil.contrato) |
            Q(contrato__isnull=True, solicitacao__contrato=perfil.contrato)
        )

    total_transito = base_count.filter(data_retorno__isnull=True).count()
    total_finalizada = base_count.filter(data_retorno__isnull=False).count()
    total_geral = base_count.count()

    return render(request, "movimentacoes/lista.html", {
        "movimentacoes": movimentacoes,
        "paginator": paginator,
        "page_obj": movimentacoes,
        "limite": limite,
        "status": status,
        "search": search,
        "inicio": inicio,
        "fim": fim,
        "total_transito": total_transito,
        "total_finalizada": total_finalizada,
        "total_geral": total_geral,
    })



# FILTRAR MOVIMENTAÇÕES (AJAX)
def filtrar_movimentacoes(request):
    # Verificar se é requisição AJAX
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    # Obter parâmetros (mantendo nomes originais)
    status = request.GET.get("status", "")
    search = request.GET.get("search", "").strip()
    inicio = request.GET.get("inicio", "")  # Voltar para "inicio"
    fim = request.GET.get("fim", "")  # Voltar para "fim"
    page = request.GET.get("page", 1)


    # Limite de itens por página
    try:
        limite = int(request.GET.get("limite", 12))
        if limite not in [5, 10, 15, 20, 30]:
            limite = 12
    except:
        limite = 12
    
    # Query base
    movs = Movimentacao.objects.select_related("veiculo", "motorista").order_by("-data_saida")

    #  FILTRO CORRETO DE CONTRATO
    perfil = getattr(request.user, "perfilusuario", None)
    
    # se for gestor, filtrar por contrato (tanto no campo direto quanto na solicitação relacionada)
    if perfil and perfil.nivel == "gestor" and perfil.contrato:
        movs = movs.filter(
            Q(contrato=perfil.contrato) |
            Q(contrato__isnull=True, solicitacao__contrato=perfil.contrato)
    )
    
    # Aplicar filtros
    if search:

        search = search.strip()

        #  Busca por TAG do veículo (ex: VA-100)
        if "-" in search and search.upper().startswith("VA"):
            movs = movs.filter(veiculo__tag_interna__iexact=search)

        #  Busca por placa exata (ABC-1234)
        elif "-" in search and len(search) >= 7:
            movs = movs.filter(veiculo__placa__iexact=search)

        #  Busca por ID da movimentação
        elif search.isdigit():
            movs = movs.filter(id=int(search))

        #  Busca geral
        else:
            movs = movs.filter(
                Q(veiculo__placa__icontains=search) |
                Q(motorista__nome__icontains=search) |
                Q(veiculo__modelo__icontains=search) |
                Q(veiculo__marca__icontains=search) |
                Q(veiculo__tag_interna__icontains=search)
            )
    
    # Filtro de status
    if status == "transito":
        movs = movs.filter(data_retorno__isnull=True)
    elif status == "finalizada":
        movs = movs.filter(data_retorno__isnull=False)
    
    if inicio:
        try:
            movs = movs.filter(data_saida__date__gte=inicio)
        except:
            pass
    
    if fim:
        try:
            movs = movs.filter(data_saida__date__lte=fim)
        except:
            pass
    
    # Paginação
    paginator = Paginator(movs, limite)
    
    try:
        movimentacoes = paginator.get_page(page)
    except:
        movimentacoes = paginator.get_page(1)
    
    # Contexto para templates
    context = {
        "movimentacoes": movimentacoes,
        "status": status,
        "search": search,
        "inicio": inicio,
        "fim": fim,
        "page_obj": movimentacoes,
        "request": request,
    }
    
    # SE for requisição AJAX, retorna JSON
    if is_ajax:
        # Renderizar templates
        html_cards = render_to_string(
            "movimentacoes/partials/cards.html",
            context,
            request=request
        )
        
        html_paginacao_mobile = render_to_string(
            "movimentacoes/partials/paginacao_mobile.html",
            context,
            request=request
        )
        
        html_paginacao_desktop = render_to_string(
            "movimentacoes/partials/paginacao_desktop.html",
            context,
            request=request
        )
        
        return JsonResponse({
            "html_cards": html_cards,
            "paginacao_mobile": html_paginacao_mobile,
            "paginacao_desktop": html_paginacao_desktop,
            "status": status,
            "count": paginator.count,
            "total_pages": paginator.num_pages,
            "current_page": movimentacoes.number,
        })
    
    # SE for requisição normal, redirecionar para lista_movimentacoes
    # (porque essa função agora é apenas para AJAX)
    return redirect("lista_movimentacoes")




# CRIAR MOVIMENTAÇÃO (MANUAL OU A PARTIR DE SOLICITAÇÃO)
@login_required
def criar_movimentacao(request):
    perfil = getattr(request.user, "perfilusuario", None)

    # VEÍCULOS EM USO (MOVIMENTAÇÃO ABERTA)
    veiculos_em_uso = Movimentacao.objects.filter(
        data_retorno__isnull=True
    ).values_list("veiculo_id", flat=True)


    # MOTORISTAS EM USO (MOVIMENTAÇÃO OU SOLICITAÇÃO ABERTA)
    motoristas_mov_em_uso = Movimentacao.objects.filter(
        data_retorno__isnull=True
    ).values_list("motorista_id", flat=True)

    motoristas_sol_em_uso = SolicitacaoVeiculo.objects.exclude(
        status="FINALIZADA"
    ).values_list("motorista_id", flat=True)

    # VEÍCULOS DISPONÍVEIS
    veiculos = Veiculo.objects.filter(
        status="Disponivel"
    ).exclude(
        id__in=veiculos_em_uso
    )

    if perfil and perfil.nivel != "adm":
        veiculos = veiculos.filter(contrato=perfil.contrato)


    # MOTORISTAS DISPONÍVEIS
    motoristas = Motorista.objects.exclude(
        id__in=list(motoristas_mov_em_uso) + list(motoristas_sol_em_uso)
    )

    if perfil and perfil.nivel != "adm":
        motoristas = motoristas.filter(contrato=perfil.contrato)


    # SOLICITAÇÃO (SE VIER)
    solicitacao_id = request.GET.get("solicitacao_id") or request.POST.get("solicitacao_id")
    solicitacao = None

    if solicitacao_id:
        solicitacao = get_object_or_404(SolicitacaoVeiculo, pk=int(solicitacao_id))

    if request.method == "POST":
    
        # DEFINIR VEÍCULO E MOTORISTA
        if solicitacao:
            veiculo = solicitacao.veiculo
            motorista = solicitacao.motorista
        else:
            veiculo_id = request.POST.get("veiculo")
            motorista_id = request.POST.get("motorista")

            if not veiculo_id or not motorista_id:
                return render(request, "movimentacoes/form.html", {
                    "veiculos": veiculos,
                    "motoristas": motoristas,
                    "error": "Veículo e motorista são obrigatórios."
                })

            veiculo = get_object_or_404(Veiculo, pk=veiculo_id)
            motorista = get_object_or_404(Motorista, pk=motorista_id)

        # VALIDAÇÕES DE SEGURANÇA (BACKEND)
        if Movimentacao.objects.filter(veiculo=veiculo, data_retorno__isnull=True).exists():
            return render(request, "movimentacoes/form.html", {
                "veiculos": veiculos,
                "motoristas": motoristas,
                "error": "Este veículo já está em movimentação."
            })

        if Movimentacao.objects.filter(motorista=motorista, data_retorno__isnull=True).exists():
            return render(request, "movimentacoes/form.html", {
                "veiculos": veiculos,
                "motoristas": motoristas,
                "error": "Este motorista já está em movimentação."
            })

        if SolicitacaoVeiculo.objects.filter(
            motorista=motorista
        ).exclude(status="FINALIZADA").exists():
            return render(request, "movimentacoes/form.html", {
                "veiculos": veiculos,
                "motoristas": motoristas,
                "error": "Este motorista possui solicitação em aberto."
            })


        # CASO 1 — GESTOR / ADM (CRIA APENAS SOLICITAÇÃO)
        if not solicitacao and perfil and perfil.nivel in ["gestor", "adm"]:

            SolicitacaoVeiculo.objects.create(
                origem="MANUAL",
                veiculo=veiculo,
                motorista=motorista,
                contrato=perfil.contrato,
                id_contrato=perfil.contrato.id if perfil.contrato else None,
                destino=request.POST.get("destino", "").upper(),
                justificativa=request.POST.get("justificativa", "").upper(),
                previsao_retorno=timezone.now(),
                status="AGUARDANDO_SAIDA_PORTARIA",

                solicitante=request.user,
                solicitante_nome=request.user.get_full_name() or request.user.username,

                gestor_responsavel=request.user,
                gestor_responsavel_nome=request.user.get_full_name() or request.user.username,
                data_aprovacao=timezone.now(),
            )

            messages.success(
                request,
                "Solicitação criada com sucesso e enviada para a portaria realizar a saída."
            )

            # NÃO cria movimentação aqui
            return redirect("listar_saidas_portaria")

        # CASO 2 — VEIO DE SOLICITAÇÃO (NUNCA CRIA MOVIMENTAÇÃO AQUI)
        messages.info(
            request,
            "Solicitação encaminhada para a portaria realizar a saída."
        )
        return redirect("listar_saidas_portaria")

    return render(request, "movimentacoes/form.html", {
        "veiculos": veiculos,
        "motoristas": motoristas,
        "solicitacao": solicitacao,
    })




# DETALHES DA MOVIMENTAÇÃO
def movimentacao_detalhe(request, pk):
    mov = get_object_or_404(Movimentacao, pk=pk)
    return render(request, "movimentacoes/detalhe.html", {"mov": mov})


# REGISTRAR RETORNO (PORTARIA)

@login_required
def registrar_retorno(request, pk):
    mov = get_object_or_404(Movimentacao, pk=pk)
    
    # DEFINIR CONTEXTO (PORTARIA x MANUAL)
    perfil = getattr(request.user, "perfilusuario", None)
    
    # Template por perfil
    if perfil and perfil.nivel == "portaria":
        template = "movimentacoes/retorno_portaria.html"
    else:
        template = "movimentacoes/retorno.html"
    
    if request.method == "POST":

        # KM RETORNO (VALIDAÇÃO)
        km_retorno_str = request.POST.get("km_retorno", "0")
        km_retorno_limpo = km_retorno_str.replace(".", "").replace(",", "")
        
        try:
            km_retorno_valor = int(km_retorno_limpo)
        except ValueError:
            km_retorno_valor = 0
        
        if km_retorno_valor <= (mov.km_saida or 0):
            messages.error(request, "O KM de retorno deve ser maior que o KM de saída.")
            return redirect(request.path)
        
        km_atual_veiculo = mov.veiculo.km_atual or 0
        if km_retorno_valor < km_atual_veiculo:
            messages.error(
                request,
                f"O KM de retorno ({km_retorno_valor}) não pode ser menor que o KM atual do veículo ({km_atual_veiculo})."
            )
            return redirect(request.path)
        

        # ATUALIZAR MOVIMENTAÇÃO
        observacao = request.POST.get("observacao", "")
        
        if perfil and perfil.nivel == "portaria":
            mov.observacao_portaria_retorno = observacao
        else:
            if observacao:
                mov.observacao = (mov.observacao or "") + f"\n[Retorno] {observacao}"
        
        mov.km_retorno = km_retorno_valor
        mov.data_retorno = timezone.now()
        mov.distancia_percorrida = km_retorno_valor - (mov.km_saida or 0)
        mov.status = "finalizado"
        

        # PORTEIRO + FOTOS (RETORNO)
        if perfil and perfil.nivel == "portaria":
            mov.porteiro_retorno = request.user
            mov.porteiro_retorno_nome = (
                request.user.get_full_name() or request.user.username
            )
            
            mov.foto_retorno_geral = request.FILES.get("foto_retorno_geral")
            mov.foto_retorno_painel = request.FILES.get("foto_retorno_painel")
            mov.foto_retorno_avaria = request.FILES.get("foto_retorno_avaria")
            mov.foto_retorno_equipamento = request.FILES.get("foto_retorno_equipamento")
            mov.foto_retorno_cacamba = request.FILES.get("foto_retorno_cacamba")
            mov.foto_retorno_prancha = request.FILES.get("foto_retorno_prancha")
            mov.foto_retorno_porta_malas = request.FILES.get("foto_retorno_porta_malas")
            mov.foto_retorno_combustivel = request.FILES.get("foto_retorno_combustivel")
        
        mov.save()
        

        # SOLICITAÇÃO VINCULADA
        if mov.solicitacao:
            mov.solicitacao.status = "FINALIZADA"
            mov.solicitacao.data_retorno = mov.data_retorno
            mov.solicitacao.save()
        

        # 👈 VEÍCULO - ATUALIZAR SEM VALIDAÇÕES (USANDO QUERY DIRETA)
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE veiculos_veiculo SET status = %s, km_atual = %s WHERE id = %s",
                ["Disponivel", km_retorno_valor, mov.veiculo.id]
            )
        
        # REDIRECT FINAL
        messages.success(request, "Retorno registrado com sucesso!")
        return redirect("lista_movimentacoes")
    
    # GET
    return render(request, template, {
        "mov": mov,
        "km_saida": mov.km_saida,
    })



# EXPORTAÇÃO COM FILTROS
def exportar_movimentacoes_excel(request):

    #   Query base com select_related para otimizar acesso a dados relacionados
    movs = Movimentacao.objects.select_related("veiculo", "motorista", "solicitacao")

    #  AQUI É O PONTO PRINCIPAL
    movs = aplicar_filtros_movimentacoes(request, movs)

    movs = movs.order_by("-data_saida")

    wb = Workbook()
    ws = wb.active
    ws.title = "Movimentações"

    headers = [
        "ID", "Placa", "Tag", "Motorista", "Destino",
        "KM Saída", "KM Retorno", "KM Percorrido",
        "Data Saída", "Data Retorno", "Status"
    ]

    ws.append(headers)

    for mov in movs:
        ws.append([
            mov.id,
            mov.veiculo.placa,
            mov.veiculo.tag_interna,
            mov.motorista.nome,
            mov.destino,
            mov.km_saida,
            mov.km_retorno or "-",
            mov.distancia_percorrida or "-",
            localtime(mov.data_saida).strftime("%d/%m/%Y %H:%M"),
            localtime(mov.data_retorno).strftime("%d/%m/%Y %H:%M") if mov.data_retorno else "-",
            "Finalizada" if mov.data_retorno else "Em Trânsito",
        ])

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="movimentacoes.xlsx"'

    wb.save(response)
    return response



# VIEWS AUXILIARES
def atualizar_filtros_session(request):
    """Armazena filtros na sessão para manter entre requisições"""
    if request.method == "GET":
        # Salvar filtros importantes
        for key in ["status", "search", "inicio", "fim"]:
            value = request.GET.get(key)
            if value is not None:
                request.session[f'filtro_{key}'] = value
    return True




# CHECKLIST DE SAÍDA (motorista)
def checklist_saida_motorista(request, solicitacao_id):
    solicitacao = get_object_or_404(SolicitacaoVeiculo, id=solicitacao_id)

    # Evitar checklist repetido
    mov_existente = Movimentacao.objects.filter(
        solicitacao=solicitacao
    ).first()

    if mov_existente and mov_existente.status != "aguardando_saida_portaria":
        messages.error(request, "Este checklist já foi preenchido.")
        return redirect("dashboard_motorista")

    if request.method == "POST":

        # 1) Criar movimentação caso ainda não exista
        if not mov_existente:
            mov = Movimentacao.objects.create(
                solicitacao=solicitacao,
                veiculo=solicitacao.veiculo,
                motorista=solicitacao.motorista,
                contrato=solicitacao.contrato,
                destino=solicitacao.destino,
                status="aguardando_saida_portaria",   # pronto para portaria
            )
        else:
            mov = mov_existente

        # 2) Criar checklist vinculado à movimentação
        ChecklistSaida.objects.create(
            movimentacao=mov,
            pneus_ok=request.POST.get("pneus_ok") == "on",
            luzes_ok=request.POST.get("luzes_ok") == "on",
            documentos_ok=request.POST.get("documentos_ok") == "on",
            avarias=request.POST.get("avarias"),
            observacoes=request.POST.get("observacoes"),
            foto_painel=request.FILES.get("foto_painel"),
            foto_frente=request.FILES.get("foto_frente"),
            foto_traseira=request.FILES.get("foto_traseira"),
            foto_lado_esq=request.FILES.get("foto_lado_esq"),
            foto_lado_dir=request.FILES.get("foto_lado_dir"),
        )

        # 3) Atualizar status da solicitação
        solicitacao.status = "AGUARDANDO_SAIDA_PORTARIA"
        solicitacao.save()

        # 4) Redirecionar motorista
        messages.success(request, "Checklist de saída enviado com sucesso!")
        return redirect("dashboard_motorista")

    return render(request, "movimentacoes/checklist_saida.html", {
        "solicitacao": solicitacao
    })



# REGISTRA A SAÍDA - PORTARIA
@login_required
def portaria_registrar_saida(request, solicitacao_id):
    solicitacao = get_object_or_404(SolicitacaoVeiculo, id=solicitacao_id)


    contrato = None

    if solicitacao and solicitacao.contrato:
        contrato = solicitacao.contrato

    elif solicitacao.veiculo and solicitacao.veiculo.contrato:
        contrato = solicitacao.veiculo.contrato

    elif request.user.perfilusuario.contrato:
        contrato = request.user.perfilusuario.contrato

    # Se movimentação ainda não existe, criar
    mov, created = Movimentacao.objects.get_or_create(
        solicitacao=solicitacao,
        defaults={
            "veiculo": solicitacao.veiculo,
            "motorista": solicitacao.motorista,
            "destino": solicitacao.destino,
            "status": "aguardando_saida_portaria",
            "origem": solicitacao.origem,
            "contrato": contrato,
        }
    )

    #  Garantir que a movimentação tenha o contrato definido (caso criada pela primeira vez sem contrato)
    if not mov.contrato:
        mov.contrato = contrato
        mov.save(update_fields=["contrato"])

    # Garantir que a movimentação tenha o contrato definido (caso criada manualmente sem solicitação)
    if not mov.contrato:
        mov.contrato = contrato
        mov.save()

    # Verificar se a movimentação já está em andamento
    if request.method == "POST":
        mov.km_saida = mov.veiculo.km_atual
        mov.data_saida = timezone.now()
        mov.status = "em_andamento"
        
        #  IMPORTANTE: Salvar observações da portaria
        mov.observacao_portaria = request.POST.get("observacao_portaria", "")
        
        # Outras observações (para compatibilidade)
        mov.observacao = request.POST.get("observacao", "")
        
        mov.foto_portaria_geral = request.FILES.get("foto_portaria_geral")
        mov.foto_portaria_avaria = request.FILES.get("foto_portaria_avaria")
        mov.foto_portaria_painel = request.FILES.get("foto_portaria_painel")
        mov.foto_portaria_equipamento = request.FILES.get("foto_portaria_equipamento")
        
        # Equipamentos especiais
        mov.com_cacamba = request.POST.get("com_cacamba") == "on"
        mov.cacamba_descricao = request.POST.get("cacamba_descricao", "")
        mov.com_prancha = request.POST.get("com_prancha") == "on"
        mov.prancha_descricao = request.POST.get("prancha_descricao", "")

        # Porteiro que liberou
        mov.porteiro_saida = request.user
        mov.porteiro_saida_nome = request.user.get_full_name() or request.user.username

        mov.save()

        solicitacao.status = "EM_TRANSITO"
        solicitacao.save()

        veiculo = mov.veiculo
        veiculo.status = "EmTransito"
        veiculo.km_anterior = veiculo.km_atual
        veiculo.save()

        messages.success(request, "Saída registrada com sucesso.")
        return redirect("/movimentacoes/?status=transito")

    return render(request, "movimentacoes/portaria/saida_registro.html", {
        "mov": mov,
        "veiculo": mov.veiculo,
    })


# RETORNO DO MOTORISTA
def checklist_retorno_motorista(request, pk):
    mov = get_object_or_404(Movimentacao, pk=pk)

    # Status incorreto? Não deixa acessar
    if mov.status != "aguardando_checklist_retorno":
        messages.error(request, "Checklist de retorno não está disponível no momento.")
        return redirect("dashboard_motorista")

    # Verifica se a portaria realmente registrou o retorno
    if not mov.km_retorno:
        messages.error(request, "A portaria ainda não registrou o retorno do veículo.")
        return redirect("dashboard_motorista")

    # Evita checklist duplicado
    if ChecklistRetorno.objects.filter(movimentacao=mov).exists():
        messages.warning(request, "O checklist de retorno já foi enviado.")
        return redirect("dashboard_motorista")

    # 2. Salvando checklist
    if request.method == "POST":

        checklist = ChecklistRetorno.objects.create(
            movimentacao=mov,
            avarias_novas=request.POST.get("avarias_novas") or "",
            observacoes=request.POST.get("observacoes") or "",
            foto_painel=request.FILES.get("foto_painel"),
            foto_frente=request.FILES.get("foto_frente"),
            foto_traseira=request.FILES.get("foto_traseira"),
            foto_lado_esq=request.FILES.get("foto_lado_esq"),
            foto_lado_dir=request.FILES.get("foto_lado_dir"),
            data_checklist=timezone.now(),  # Auditoria
        )


        # 3. Finalizar movimentação
        mov.status = "finalizado"
        mov.data_retorno = mov.data_retorno or timezone.now()
        mov.save()


        # 4. Atualizar solicitação
        if mov.solicitacao:
            mov.solicitacao.status = "FINALIZADA"
            mov.solicitacao.data_retorno = mov.data_retorno
            mov.solicitacao.save()


        # 5. Atualizar veículo
        veiculo = mov.veiculo
        veiculo.status = "Disponivel"
        veiculo.km_atual = mov.km_retorno  # KM REAL
        veiculo.save()

        messages.success(
            request,
            "Checklist de retorno enviado com sucesso! Movimentação finalizada."
        )
        return redirect("dashboard_motorista")


    # 6. Renderizar formulário
    return render(request, "movimentacoes/checklist_retorno.html", {
        "mov": mov
    })



#REGISTRA A ENTRADA NA PORTARIA
# movimentacoes/views.py - Atualize a view terceiro_entrada
@login_required
def terceiro_entrada(request):
    if request.method == "POST":
        MovimentacaoTerceiro.objects.create(
            placa=request.POST.get("placa").upper(),
            tipo_veiculo=request.POST.get("tipo_veiculo"),
            empresa=request.POST.get("empresa").upper(),
            motorista_nome=request.POST.get("motorista_nome").upper(),
            documento=request.POST.get("documento"),
            
            descricao_veiculo=request.POST.get("descricao_veiculo", ""),
            tags=request.POST.get("tags", "").upper(),
            
            # 🔹 NOVOS CAMPOS
            motivo_entrada=request.POST.get("motivo", ""),
            observacoes_entrada=request.POST.get("observacoes", ""),
            
            status="ENTRADA",
            
            porteiro_entrada=request.user,
            porteiro_entrada_nome=request.user.get_full_name() or request.user.username,
            
            foto_placa=request.FILES.get("foto_placa"),
            foto_veiculo=request.FILES.get("foto_veiculo"),
            foto_motorista=request.FILES.get("foto_motorista"),
        )
        
        messages.success(request, "Entrada registrada com sucesso.")
        return redirect("terceiros_portaria_lista")
    
    return render(request, "movimentacoes/terceiros/entrada.html")



# LISTA PARA PORTARIA REGISTRAR ENTRADA/SAÍDA DE TERCEIROS + FILTROS + ESTATÍSTICAS
@login_required
def terceiros_portaria_lista(request):
    perfil = getattr(request.user, "perfilusuario", None)

    if not perfil or perfil.nivel not in ["portaria", "gestor", "adm"]:
        messages.error(request, "Acesso não autorizado.")
        return redirect("dashboard")

    status = request.GET.get("status", "abertos")
    inicio = request.GET.get("inicio")
    fim = request.GET.get("fim")

    qs = MovimentacaoTerceiro.objects.all().order_by("-data_entrada")

    if status == "abertos":
        qs = qs.filter(status="ENTRADA")
    elif status == "finalizados":
        qs = qs.filter(status="SAIDA")

    if inicio:
        qs = qs.filter(data_entrada__date__gte=inicio)

    if fim:
        qs = qs.filter(data_entrada__date__lte=fim)

    # CALCULAR ESTATÍSTICAS DO DASHBOARD (SEMPRE MOSTRAR TOTAL)
    from django.utils import timezone
    from datetime import timedelta

    # Total geral
    total_registros = MovimentacaoTerceiro.objects.count()
    
    # No pátio (ENTRADA sem data de saída)
    no_patio = MovimentacaoTerceiro.objects.filter(
        status="ENTRADA"
    ).count()
    
    # Finalizados (SAIDA)
    finalizados = MovimentacaoTerceiro.objects.filter(
        status="SAIDA"
    ).count()

    # Hoje
    hoje = timezone.now().date()
    hoje_entradas = MovimentacaoTerceiro.objects.filter(
        data_entrada__date=hoje
    ).count()
    
    hoje_saidas = MovimentacaoTerceiro.objects.filter(
        status="SAIDA",
        data_saida__date=hoje
    ).count()

    # Últimos 7 dias
    sete_dias_atras = hoje - timedelta(days=7)
    ultimos_7_dias = MovimentacaoTerceiro.objects.filter(
        data_entrada__date__gte=sete_dias_atras
    ).count()

    # Para a contagem no footer, use o qs filtrado
    movimentacoes_count = qs.count()

    return render(
        request,
        "movimentacoes/terceiros/lista_portaria.html",
        {
            "movimentacoes": qs,
            "status_atual": status,
            "inicio": inicio,
            "fim": fim,
            "total_registros": total_registros,
            "no_patio": no_patio,
            "finalizados": finalizados,
            "hoje_entradas": hoje_entradas,
            "hoje_saidas": hoje_saidas,
            "ultimos_7_dias": ultimos_7_dias,
            "movimentacoes_count": movimentacoes_count,  # Para o footer
            "now": timezone.now(),  # Para timestamp
        }
    )


from openpyxl import Workbook
from django.http import HttpResponse

# EXPORTAÇÃO DE TERCEIROS COM FILTROS
@login_required
def exportar_terceiros_excel(request):

    status = request.GET.get("status", "todos")
    inicio = request.GET.get("inicio")
    fim = request.GET.get("fim")

    qs = MovimentacaoTerceiro.objects.all().order_by("-data_entrada")

    if status == "abertos":
        qs = qs.filter(status="ENTRADA")
    elif status == "finalizados":
        qs = qs.filter(status="SAIDA")

    if inicio:
        qs = qs.filter(data_entrada__date__gte=inicio)
    if fim:
        qs = qs.filter(data_entrada__date__lte=fim)

    wb = Workbook()
    ws = wb.active
    ws.title = "Veículos de Terceiros"

    ws.append([
        "Placa", "Empresa", "Motorista",
        "Entrada", "Saída", "Status"
    ])

    for mov in qs:
        ws.append([
            mov.placa,
            mov.empresa,
            mov.motorista_nome,
            mov.data_entrada.strftime("%d/%m/%Y %H:%M"),
            mov.data_saida.strftime("%d/%m/%Y %H:%M") if mov.data_saida else "-",
            mov.status
        ])

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="veiculos_terceiros.xlsx"'
    wb.save(response)

    return response


# REGISTRA A SAÍDA NA PORTARIA
@login_required
def terceiro_saida(request, pk):
    perfil = getattr(request.user, "perfilusuario", None)

    #  Perfil básico não acessa
    if not perfil or perfil.nivel not in ["portaria", "gestor", "adm"]:
        messages.error(request, "Acesso não autorizado.")
        return redirect("dashboard")

    mov = get_object_or_404(
        MovimentacaoTerceiro,
        pk=pk,
        status="ENTRADA"
    )
    
    # POST → somente PORTARIA pode registrar a saída
    if request.method == "POST":
        #if perfil.nivel != "portaria": # SOMENTE PORTARIA REGISTRA SAÍDA, MAS GESTOR/ADM PODEM VISUALIZAR DETALHES
        if perfil.nivel not in ["portaria", "adm", "gestor"]: # PERMITIR GESTOR/ADM REGISTRAREM SAÍDA (CASO PORTARIA NÃO ESTEJA DISPONÍVEL)
            messages.error(request, "Apenas a portaria pode registrar a saída do veículo.")
            return redirect("terceiros_portaria_lista")
        
        mov.data_saida = timezone.now()
        mov.porteiro_saida = request.user
        mov.porteiro_saida_nome = request.user.get_full_name() or request.user.username
        
        #  SALVAR OBSERVAÇÕES DA SAÍDA
        mov.observacoes_saida = request.POST.get("observacoes", "")
        
        mov.status = "SAIDA"
        mov.save()
        
        messages.success(request, "Saída registrada com sucesso.")
        return redirect("terceiros_portaria_lista")

    # GET → qualquer perfil autorizado pode VISUALIZAR
    return render(
        request,
        "movimentacoes/terceiros/saida.html",
        {"mov": mov}
    )



# HISTÓRICO DE TERCEIROS (TODOS OS REGISTROS, COM FILTROS)
@login_required
def terceiros_historico(request):
    perfil = getattr(request.user, "perfilusuario", None)

    if not perfil or perfil.nivel not in ["gestor", "adm"]:
        messages.error(request, "Acesso não autorizado.")
        return redirect("dashboard")

    qs = MovimentacaoTerceiro.objects.all().order_by("-data_entrada")

    status = request.GET.get("status")
    placa = request.GET.get("placa")
    empresa = request.GET.get("empresa")
    inicio = request.GET.get("inicio")
    fim = request.GET.get("fim")

    if status:
        qs = qs.filter(status=status)
    if placa:
        qs = qs.filter(placa__icontains=placa)
    if empresa:
        qs = qs.filter(empresa__icontains=empresa)
    if inicio:
        qs = qs.filter(data_entrada__date__gte=inicio)
    if fim:
        qs = qs.filter(data_entrada__date__lte=fim)

    return render(
        request,
        "movimentacoes/terceiros/historico.html",
        {
            "movimentacoes": qs,
        }
    )

# DETALHES DA MOVIMENTAÇÃO DE TERCEIRO
@login_required
def terceiros_detalhe(request, pk):
    mov = get_object_or_404(MovimentacaoTerceiro, pk=pk)

    perfil = getattr(request.user, "perfilusuario", None)
    #  Perfil básico não acessa detalhes
    if not perfil or perfil.nivel not in ["gestor", "adm","portaria"]:
        messages.error(request, "Acesso não autorizado.")
        return redirect("dashboard")

    return render(
        request,
        "movimentacoes/terceiros/detalhe.html",
        {
            "mov": mov
        }
    )