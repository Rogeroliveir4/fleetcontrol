from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from veiculos.models import Veiculo
from contratos.models import Contrato
from contas.models import PerfilUsuario
from motoristas.models import Motorista
from solicitacoes.models import SolicitacaoVeiculo
from django.db.models import Exists, OuterRef
# views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt
from .models import Veiculo, Contrato
from .forms import VeiculoForm
from django.urls import reverse
from datetime import datetime, timedelta

# ----------------------------------------------------------------------
# LISTAGEM DE VEÍCULOS
# ----------------------------------------------------------------------
def lista_veiculos(request):

    perfil, created = PerfilUsuario.objects.get_or_create(
        user=request.user,
        defaults={"nivel": "basico"}
    )

    # Filtros GET
    status_filter = request.GET.get('status', '').strip()
    search_query = request.GET.get('search', '').strip()
    categoria_filter = request.GET.get('categoria', '').strip()
    localizacao_filter = request.GET.get('localizacao', '').strip()

    # Base inicial
    veiculos_list = Veiculo.objects.all().order_by("-ativo", "placa")

    # 🔥 Filtrar por contrato (gestor/motorista)
    if perfil.nivel != "adm" and perfil.contrato_id:
        veiculos_list = veiculos_list.filter(contrato_id=perfil.contrato_id)

    # 🔒 Motorista só vê veículos disponíveis
    if perfil.nivel == "basico":
        veiculos_list = veiculos_list.all()

    # ---------------------------------------------------------------
    # 🔥 ANOTAR se o veículo possui solicitação pendente
    # ---------------------------------------------------------------
    veiculos_list = veiculos_list.annotate(
        solicitacao_pendente=Exists(
            SolicitacaoVeiculo.objects.filter(
                veiculo_id=OuterRef("pk"),
                status__in=[
                    "PENDENTE",
                    "AGUARDANDO_CHECKLIST_SAIDA",
                    "AGUARDANDO_SAIDA_PORTARIA",
                    "EM_ANDAMENTO",
                    "AGUARDANDO_CHECKLIST_RETORNO",
                ]
            )
        )
    )

    # ---------------------------------------------------------------
    # 🔥 Solicitação pendente DO USUÁRIO (motorista, gestor, adm)
    # ---------------------------------------------------------------
    solicitacao_do_motorista = None
    solicitacao_ativa = False

    motorista = Motorista.objects.filter(user=request.user).first()
    
    if motorista:
        solicitacao_do_motorista = SolicitacaoVeiculo.objects.filter(
            motorista=motorista,
            status__in=[
            "PENDENTE",
            "AGUARDANDO_CHECKLIST_SAIDA",
            "AGUARDANDO_SAIDA_PORTARIA",
            "EM_ANDAMENTO",
            "AGUARDANDO_CHECKLIST_RETORNO"
        ]
        ).first()

        # Se existe solicitação ativa, bloquear solicitação em todos os perfis
        solicitacao_ativa = solicitacao_do_motorista is not None


    # ---------------------------------------------------------------
    #  Filtragem por status
    # ---------------------------------------------------------------
    if status_filter:
        mapa_status = {
            "disponivel": "Disponivel",
            "manutencao": "Manutencao",
        }

        if status_filter == "inativo":
            veiculos_list = veiculos_list.filter(ativo=False)

        elif status_filter in mapa_status:
            veiculos_list = veiculos_list.filter(
                ativo=True, status=mapa_status[status_filter]
            )

        elif status_filter == "indisponivel":
            veiculos_list = veiculos_list.filter(ativo=True).exclude(
                status="Disponivel"
            ).exclude(status="Manutencao")

        elif status_filter in dict(Veiculo.STATUS_CHOICES):
            veiculos_list = veiculos_list.filter(
                ativo=True, status=status_filter
            )

    else:
        veiculos_list = veiculos_list.filter(ativo=True)

    # ---------------------------------------------------------------
    # 🔥 Busca geral
    # ---------------------------------------------------------------
    if search_query:
        veiculos_list = veiculos_list.filter(
            Q(placa__icontains=search_query) |
            Q(modelo__icontains=search_query) |
            Q(marca__icontains=search_query) |
            Q(renavam__icontains=search_query) |
            Q(tag_interna__icontains=search_query) |
            Q(tag_cliente__icontains=search_query) |
            Q(contrato__nome__icontains=search_query)
        )

    # Filtro categoria
    if categoria_filter:
        veiculos_list = veiculos_list.filter(categoria=categoria_filter)

    # Filtro localização
    if localizacao_filter and hasattr(Veiculo, "localizacao"):
        veiculos_list = veiculos_list.filter(localizacao__icontains=localizacao_filter)

    # ---------------------------------------------------------------
    # 🔥 CONTAGENS AJUSTADAS
    # ---------------------------------------------------------------
    if perfil.nivel == "adm":
        base_qs = Veiculo.objects.all()
    else:
        base_qs = Veiculo.objects.filter(contrato_id=perfil.contrato_id)

    total_geral = base_qs.count()
    total_ativos = base_qs.filter(ativo=True).count()
    total_inativos = base_qs.filter(ativo=False).count()
    total_disponivel = base_qs.filter(status="Disponivel", ativo=True).count()
    total_manutencao = base_qs.filter(status="Manutencao", ativo=True).count()
    total_indisponivel = base_qs.filter(ativo=True).exclude(
        status="Disponivel"
    ).exclude(status="Manutencao").count()

    # ---------------------------------------------------------------
    # 🔥 Paginação
    # ---------------------------------------------------------------
    page = request.GET.get("page", 1)
    paginator = Paginator(veiculos_list, 10)
    veiculos = paginator.get_page(page)

    # ---------------------------------------------------------------
    # 🔥 AJAX RESPONSE
    # ---------------------------------------------------------------
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({
            "html_cards": render_to_string("veiculos/partials/cards.html", {
                "veiculos": veiculos,
                "solicitacao_ativa": solicitacao_ativa,
                "solicitacao_do_motorista": solicitacao_do_motorista,
            }),
            "paginacao_mobile": render_to_string("veiculos/partials/paginacao_mobile.html", {"veiculos": veiculos}),
            "paginacao_desktop": render_to_string("veiculos/partials/paginacao_desktop.html", {"veiculos": veiculos}),
            "status": status_filter,
            "total_geral": total_geral,
            "total_ativos": total_ativos,
            "total_inativos": total_inativos,
            "total_disponivel": total_disponivel,
            "total_manutencao": total_manutencao,
            "total_indisponivel": total_indisponivel,
        })

    # ---------------------------------------------------------------
    # 🔥 RENDER FINAL
    # ---------------------------------------------------------------
    return render(request, "veiculos/lista.html", {
        "veiculos": veiculos,
        "solicitacao_ativa": solicitacao_ativa,
        "solicitacao_do_motorista": solicitacao_do_motorista,
        "status": status_filter,
        "search": search_query,
        "categoria": categoria_filter,
        "localizacao": localizacao_filter,
        "total_geral": total_geral,
        "total_ativos": total_ativos,
        "total_inativos": total_inativos,
        "total_disponivel": total_disponivel,
        "total_manutencao": total_manutencao,
        "total_indisponivel": total_indisponivel,
    })


@require_GET
def check_placa(request):
    """Verifica se uma placa já existe"""
    placa = request.GET.get('placa', '').upper().strip()
    exclude_id = request.GET.get('exclude_id', None)
    
    if not placa:
        return JsonResponse({'exists': False})
    
    # Remove formatação para busca
    placa_clean = placa.replace('-', '').replace(' ', '')
    
    # Query inicial
    qs = Veiculo.objects.filter(
        placa__iregex=r'^{}$|^{}$'.format(placa, placa_clean)
    )
    
    # Exclui o próprio veículo se for edição
    if exclude_id:
        qs = qs.exclude(id=exclude_id)
    
    exists = qs.exists()
    return JsonResponse({'exists': exists})

@require_GET
def check_tag_interna(request):
    """Verifica se uma tag interna já existe"""
    tag_interna = request.GET.get('tag_interna', '').strip()
    exclude_id = request.GET.get('exclude_id', None)
    
    if not tag_interna:
        return JsonResponse({'exists': False})
    
    # Query inicial
    qs = Veiculo.objects.filter(tag_interna__iexact=tag_interna)
    
    # Exclui o próprio veículo se for edição
    if exclude_id:
        qs = qs.exclude(id=exclude_id)
    
    exists = qs.exists()
    return JsonResponse({'exists': exists})


# ----------------------------------------------------------------------
# CRIAR VEÍCULO (com validações completas)
# ----------------------------------------------------------------------
def criar_veiculo(request):

    if request.method == "POST":

        # Normalização dos campos
        placa = request.POST.get("placa", "").upper().strip()
        tag_interna = (request.POST.get("tag_interna") or "").strip()
        #tag_cliente = (request.POST.get("tag_cliente") or "").strip()
        renavam = (request.POST.get("renavam") or "").strip()
        apolice = (request.POST.get("apolice_numero") or "").strip()

        # Função auxiliar para retornar o form com contratos
        def render_form_com_erro(msg):
            messages.error(request, msg)
            return render(request, "veiculos/novo_veiculo.html", {
                "contratos": Contrato.objects.all().order_by("id")
            })

        # -----------------------
        #  1. Validar PLACA
        # -----------------------
        if not placa:
            return render_form_com_erro("Placa é obrigatória!")

        if Veiculo.objects.filter(placa=placa).exists():
            return render_form_com_erro("Já existe outro veículo com essa placa!")

        # -----------------------
        #  2. Validar TAG INTERNA
        # -----------------------
        if tag_interna and Veiculo.objects.filter(tag_interna=tag_interna).exists():
            return render_form_com_erro("Já existe outro veículo com esta TAG interna!")

        # -----------------------
        #  3. Validar TAG CLIENTE
        # -----------------------
        #if tag_cliente and Veiculo.objects.filter(tag_cliente=tag_cliente).exists():
            #return render_form_com_erro("Já existe outro veículo com esta TAG do cliente!")

        # -----------------------
        #  4. Validar RENAVAM
        # -----------------------
        if renavam and Veiculo.objects.filter(renavam=renavam).exists():
            return render_form_com_erro("Já existe outro veículo com este Renavam!")

        # -----------------------
        #  5. Validar APÓLICE
        # -----------------------
        if apolice and Veiculo.objects.filter(apolice_numero=apolice).exists():
            return render_form_com_erro("Número de apólice já cadastrado para outro veículo!")

        # -----------------------
        # CONTRATO
        # -----------------------
        contrato_id = request.POST.get("id_contrato")
        contrato_obj = Contrato.objects.filter(id=contrato_id).first() if contrato_id else None

        # -----------------------
        # Salvar veículo
        # -----------------------
        veiculo = Veiculo.objects.create(
            contrato=contrato_obj,
            placa=placa,
            modelo=request.POST.get("modelo", "").strip(),
            marca=request.POST.get("marca", "").strip(),
            ano=request.POST.get("ano"),
            km_atual=request.POST.get("km_atual", 0).replace(".", ""),
            cor=request.POST.get("cor", "").strip(),
            categoria=request.POST.get("categoria"),
            status=request.POST.get("status", "Disponivel"),
            renavam=renavam,
            tipo=request.POST.get("tipo"),
            combustivel=request.POST.get("combustivel"),
            tipo_propriedade=request.POST.get("tipo_propriedade"),
            tag_interna=tag_interna,
            #tag_cliente=tag_cliente,
            licenciamento_vencimento=request.POST.get("licenciamento_vencimento") or None,
            seguro=request.POST.get("seguro") == "True",
            seguro_validade=request.POST.get("seguro_validade") or None,
            apolice_numero=apolice,
            observacoes=request.POST.get("observacoes", "").strip(),
            ativo=True,
        )

        messages.success(request, f"Veículo {placa} cadastrado com sucesso!")
        return redirect("detalhes_veiculo", id=veiculo.id)

    # GET → carregar form com contratos
    return render(request, "veiculos/novo_veiculo.html", {
        "contratos": Contrato.objects.all().order_by("id")
    })




# ----------------------------------------------------------------------
# EDITAR VEÍCULO (com validações completas + AJAX)
# ----------------------------------------------------------------------
def editar_veiculo(request, id):
    veiculo = get_object_or_404(Veiculo, id=id)

    # Função para respostas AJAX
    def ajax_response(success, message, errors=None, redirect_url=None):
        response_data = {
            'success': success,
            'message': message,
        }
        if errors:
            response_data['errors'] = errors
        if redirect_url:
            response_data['redirect_url'] = redirect_url
        return JsonResponse(response_data, status=200 if success else 400)

    # Função auxiliar para retornar o form com contratos sempre carregados
    def render_form_com_contratos(msg=None):
        if msg:
            messages.error(request, msg)

        return render(request, "veiculos/editar.html", {
            "veiculo": veiculo,
            "contratos": Contrato.objects.all().order_by("id"),
        })

    if request.method == "POST":
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        # Normalização de campos
        placa = request.POST.get("placa", "").upper().strip()
        tag_interna = (request.POST.get("tag_interna") or "").strip()
        tag_cliente = (request.POST.get("tag_cliente") or "").strip()
        renavam = (request.POST.get("renavam") or "").strip()
        apolice = (request.POST.get("apolice_numero") or "").strip()
        ativo = request.POST.get("ativo") == "True"  # CORREÇÃO AQUI!

        errors = {}

        # ---------------------------------------------
        #  1) Validar PLACA
        # ---------------------------------------------
        if not placa:
            errors['placa'] = ["Placa é obrigatória!"]
        elif placa != veiculo.placa and Veiculo.objects.filter(placa=placa).exists():
            errors['placa'] = ["Já existe outro veículo com esta placa!"]

        # ---------------------------------------------
        #  2) Validar TAG INTERNA
        # ---------------------------------------------
        if tag_interna and tag_interna != veiculo.tag_interna:
            if Veiculo.objects.filter(tag_interna=tag_interna).exclude(id=id).exists():
                errors['tag_interna'] = ["Já existe outro veículo com esta TAG Interna!"]

            # ---------------------------------------------
        #  3) Validar TAG CLIENTE
        # ---------------------------------------------
        #if tag_cliente and tag_cliente != veiculo.tag_cliente:
           # if Veiculo.objects.filter(tag_cliente=tag_cliente).exclude(id=id).exists():
               #errors['tag_cliente'] = ["Já existe outro veículo com esta TAG do Cliente!"]


        # ---------------------------------------------
        #  4) Validar RENAVAM
        # ---------------------------------------------
        if renavam and renavam != veiculo.renavam:
            if Veiculo.objects.filter(renavam=renavam).exclude(id=id).exists():
                errors['renavam'] = ["Já existe outro veículo com este Renavam!"]

        # ---------------------------------------------
        #  5) Validar APÓLICE
        # ---------------------------------------------
        if apolice and apolice != veiculo.apolice_numero:
            if Veiculo.objects.filter(apolice_numero=apolice).exclude(id=id).exists():
                errors['apolice_numero'] = ["Este número de apólice já está vinculado a outro veículo!"]

        # ---------------------------------------------
        #  6) Campos obrigatórios básicos
        # ---------------------------------------------
        if not request.POST.get("modelo"):
            errors['modelo'] = ["Modelo é obrigatório!"]
        if not request.POST.get("marca"):
            errors['marca'] = ["Marca é obrigatória!"]
        if not request.POST.get("ano"):
            errors['ano'] = ["Ano é obrigatório!"]

        # Se houver erros, retorna
        if errors:
            if is_ajax:
                return ajax_response(False, "Por favor, corrija os erros abaixo.", errors)
            else:
                # Para requests não-AJAX, junta todos os erros
                error_messages = []
                for field_msgs in errors.values():
                    error_messages.extend(field_msgs)
                return render_form_com_contratos("<br>".join(error_messages))

        # ---------------------------------------------
        #  7) Atualizar CONTRATO
        # ---------------------------------------------
        contrato_id = request.POST.get("id_contrato")
        contrato_obj = Contrato.objects.filter(id=contrato_id).first() if contrato_id else None

        # ---------------------------------------------
        #  8) Atualização dos demais campos
        # ---------------------------------------------
        try:
            # Campos obrigatórios
            veiculo.contrato = contrato_obj
            veiculo.placa = placa
            veiculo.modelo = request.POST.get("modelo", "").strip()
            veiculo.marca = request.POST.get("marca", "").strip()
            veiculo.ano = request.POST.get("ano")
            
            # KM (remove pontos da formatação)
            km_atual_str = request.POST.get("km_atual", "0").replace(".", "")
            veiculo.km_atual = int(km_atual_str) if km_atual_str.isdigit() else 0
            
            # Demais campos
            veiculo.cor = request.POST.get("cor", "").strip()
            veiculo.categoria = request.POST.get("categoria")
            veiculo.status = request.POST.get("status", "Disponivel")
            veiculo.renavam = renavam
            veiculo.tipo = request.POST.get("tipo")
            veiculo.combustivel = request.POST.get("combustivel")
            veiculo.tipo_propriedade = request.POST.get("tipo_propriedade")
            veiculo.tag_interna = tag_interna
            veiculo.tag_cliente = tag_cliente
            veiculo.licenciamento_vencimento = request.POST.get("licenciamento_vencimento") or None
            veiculo.seguro = request.POST.get("seguro") == "True"
            veiculo.seguro_validade = request.POST.get("seguro_validade") or None
            veiculo.apolice_numero = apolice
            veiculo.observacoes = request.POST.get("observacoes", "").strip()
            veiculo.ativo = ativo  # CORREÇÃO: usa o valor do formulário!

            veiculo.save()

            # Resposta de sucesso
            success_message = f"Veículo {veiculo.placa} atualizado com sucesso!"
            
            if is_ajax:
                return ajax_response(
                    True, 
                    success_message, 
                    redirect_url=reverse("detalhes_veiculo", args=[veiculo.id])
                )
            else:
                messages.success(request, success_message)
                return redirect("detalhes_veiculo", id=veiculo.id)

        except Exception as e:
            error_msg = f"Erro ao salvar veículo: {str(e)}"
            if is_ajax:
                return ajax_response(False, error_msg)
            else:
                return render_form_com_contratos(error_msg)

    # GET → tela de edição
    return render_form_com_contratos()


# ----------------------------------------------------------------------
# EXCLUIR VEÍCULO
# ----------------------------------------------------------------------
def excluir_veiculo(request, id):
    veiculo = get_object_or_404(Veiculo, id=id)
    
    if request.method == "POST":
        placa = veiculo.placa
        veiculo.delete()
        messages.success(request, f"Veículo {placa} excluído com sucesso!")
        return redirect("lista_veiculos")
    
    return render(request, "veiculos/confirmar_exclusao.html", {"veiculo": veiculo})





# DETALHES DO VEÍCULO
def detalhes_veiculo(request, id):
    veiculo = get_object_or_404(Veiculo, id=id)
    
    # Histórico de movimentações (se houver modelo relacionado)
    historico_movimentacoes = []
    try:
        from movimentacoes.models import Movimentacao
        historico_movimentacoes = Movimentacao.objects.filter(
            veiculo=veiculo
        ).order_by('-data_saida')[:10]
    except:
        pass
    
    context = {
        'veiculo': veiculo,
        'historico_movimentacoes': historico_movimentacoes,
    }
    
    return render(request, "veiculos/detalhes_veiculo.html", context)


# EXPORTAR VEÍCULOS PARA EXCEL
def exportar_excel(request):
    perfil, created = PerfilUsuario.objects.get_or_create(
        user=request.user,
        defaults={"contrato": "Geral", "nivel": "basico"}
    )

    # Filtros recebidos via GET
    status_filter = request.GET.get("status", "").strip()
    search_query = request.GET.get("search", "").strip()
    categoria_filter = request.GET.get("categoria", "").strip()
    localizacao_filter = request.GET.get("localizacao", "").strip()
    contrato_filter = request.GET.get("contrato", "").strip()

    # Base - exportar tanto ativos quanto inativos se solicitado
    veiculos = Veiculo.objects.all().order_by("-ativo", "placa")

    # Permissão por contrato (não ADM)
    if perfil.nivel != "adm" and perfil.contrato:
        veiculos = veiculos.filter(contrato=perfil.contrato)

    # Filtro status
    if status_filter:
        mapa = {
            "disponivel": "Disponivel",
            "manutencao": "Manutencao",
        }
        
        if status_filter == "inativo":
            veiculos = veiculos.filter(ativo=False)
        elif status_filter in mapa:
            veiculos = veiculos.filter(ativo=True, status=mapa[status_filter])
        elif status_filter == "indisponivel":
            veiculos = veiculos.filter(ativo=True).exclude(status="Disponivel").exclude(status="Manutencao")
        else:
            if status_filter in dict(Veiculo.STATUS_CHOICES):
                veiculos = veiculos.filter(ativo=True, status=status_filter)

    # Filtro de busca
    if search_query:
        veiculos = veiculos.filter(
            Q(placa__icontains=search_query) |
            Q(modelo__icontains=search_query) |
            Q(marca__icontains=search_query) |
            Q(renavam__icontains=search_query) |
            Q(tag_interna__icontains=search_query) |
            Q(tag_cliente__icontains=search_query) |
            Q(contrato__icontains=search_query)
        )

    # Filtro categoria
    if categoria_filter:
        veiculos = veiculos.filter(categoria=categoria_filter)

    # Filtro localização (se existir no model)
    if localizacao_filter and hasattr(Veiculo, "localizacao"):
        veiculos = veiculos.filter(localizacao__icontains=localizacao_filter)

    # Filtro contrato
    if contrato_filter:
        veiculos = veiculos.filter(contrato__iexact=contrato_filter)

    # Criar workbook
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Veículos"

    # Estilo cabeçalho
    header_font = Font(bold=True)
    header_fill = PatternFill(start_color="00594C", end_color="00594C", fill_type="solid")
    header_align = Alignment(horizontal="center", vertical="center")

    headers = [
        "Ativo",
        "Placa",
        "Contrato",
        "Tag Interna",
        "Tag Cliente",
        "Marca",
        "Modelo",
        "Ano",
        "Cor",
        "Categoria",
        "Tipo",
        "Combustível",
        "KM Atual",
        "Propriedade",
        "Status",
        "Renavam",
        "IPVA Venc.",
        "Licenciamento Venc.",
        "Seguro Ativo",
        "Validade Seguro",
        "Apólice",
        "Observações",
    ]

    # Escrever cabeçalhos
    for col, header in enumerate(headers, start=1):
        cell = sheet.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        sheet.column_dimensions[cell.column_letter].width = max(len(header) + 2, 14)

    # Escrever dados
    for row, v in enumerate(veiculos, start=2):
        sheet.cell(row=row, column=1, value="Sim" if v.ativo else "Não")
        sheet.cell(row=row, column=2, value=v.placa)
        sheet.cell(row=row, column=3, value=str(v.contrato) if v.contrato else "")  # CONVERTE PARA STRING
        sheet.cell(row=row, column=4, value=v.tag_interna)
        sheet.cell(row=row, column=5, value=v.tag_cliente)
        sheet.cell(row=row, column=6, value=v.marca)
        sheet.cell(row=row, column=7, value=v.modelo)
        sheet.cell(row=row, column=8, value=v.ano)
        sheet.cell(row=row, column=9, value=v.cor)
        sheet.cell(row=row, column=10, value=v.categoria)
        sheet.cell(row=row, column=11, value=v.tipo)
        sheet.cell(row=row, column=12, value=v.combustivel)
        sheet.cell(row=row, column=13, value=v.km_atual)
        sheet.cell(row=row, column=14, value=v.tipo_propriedade)
        sheet.cell(row=row, column=15, value=v.status)
        sheet.cell(row=row, column=16, value=v.renavam)
        sheet.cell(row=row, column=17, value=v.ipva_vencimento.strftime("%d/%m/%Y") if v.ipva_vencimento else "")
        sheet.cell(row=row, column=18, value=v.licenciamento_vencimento.strftime("%d/%m/%Y") if v.licenciamento_vencimento else "")
        sheet.cell(row=row, column=19, value="Sim" if v.seguro else "Não")
        sheet.cell(row=row, column=20, value=v.seguro_validade.strftime("%d/%m/%Y") if v.seguro_validade else "")
        sheet.cell(row=row, column=21, value=v.apolice_numero)
        sheet.cell(row=row, column=22, value=v.observacoes)

    # CORREÇÃO AQUI: Remover save_virtual_workbook e usar BytesIO
    from io import BytesIO
    
    # Criar buffer em memória
    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)  # Voltar para o início do buffer
    
    # Adicionar timestamp ao nome do arquivo
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"veiculos_{timestamp}.xlsx"
    
    # Responder com arquivo
    response = HttpResponse(
        buffer.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response




# VIEW PARA ATUALIZAR KM DO VEÍCULO
def atualizar_km(request, id):
    veiculo = get_object_or_404(Veiculo, id=id)
    
    if request.method == "POST":
        try:
            novo_km = request.POST.get("novo_km")
            if novo_km:
                veiculo.km_atual = novo_km
                veiculo.save()
                messages.success(request, f"KM atualizado para {novo_km} km")
        except Exception as e:
            messages.error(request, f"Erro ao atualizar KM: {str(e)}")
    
    return redirect("detalhes_veiculo", id=id)


# VIEW PARA ALTERAR STATUS DO VEÍCULO
def alterar_status(request, id):
    veiculo = get_object_or_404(Veiculo, id=id)
    
    if request.method == "POST":
        try:
            novo_status = request.POST.get("novo_status")
            if novo_status in dict(Veiculo.STATUS_CHOICES).keys():
                veiculo.status = novo_status
                veiculo.save()
                messages.success(request, f"Status alterado para {veiculo.get_status_display()}")
        except Exception as e:
            messages.error(request, f"Erro ao alterar status: {str(e)}")
    
    return redirect("detalhes_veiculo", id=id)