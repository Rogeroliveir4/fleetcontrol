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
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt
from .models import Veiculo, Contrato
from .forms import VeiculoForm
from django.urls import reverse
from datetime import datetime, timedelta
import pandas as pd
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from veiculos.models import  HistoricoKM
from openpyxl import Workbook
import traceback
import re
from datetime import date
from django.http import HttpResponse
from openpyxl import Workbook
from collections import defaultdict
from .utils import validar_placa, formatar_placa, obter_tipo_placa



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

    #  Filtrar por contrato (gestor/motorista)
    if perfil.nivel != "adm" and perfil.contrato_id:
        veiculos_list = veiculos_list.filter(contrato_id=perfil.contrato_id)

    #  Motorista só vê veículos disponíveis
    if perfil.nivel == "basico":
        veiculos_list = veiculos_list.all()

    # ---------------------------------------------------------------
    #  ANOTAR se o veículo possui solicitação pendente
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
    #  Solicitação pendente DO USUÁRIO (motorista, gestor, adm)
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
    #  Busca geral
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
    #  CONTAGENS AJUSTADAS
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
    #  Paginação
    # ---------------------------------------------------------------
    page = request.GET.get("page", 1)
    paginator = Paginator(veiculos_list, 10)
    veiculos = paginator.get_page(page)

    # ---------------------------------------------------------------
    #  AJAX RESPONSE
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
    #  RENDER FINAL
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



# EXCLUIR VEÍCULO, (APENAS INATIVA)
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



# IMPORTAR VEÍCULOS VIA EXCEL
# veiculos/views.py

@login_required
def importar_veiculos(request):
    """View para importar veículos via Excel com pré-validação"""
    
    perfil = request.user.perfilusuario
    
    # Verificar se é ADM
    if perfil.nivel != "adm":
        messages.error(request, "Apenas administradores podem importar dados.")
        return redirect("lista_veiculos")
    
    # Limpar sessão ao acessar a página GET
    if request.method == "GET":
        if 'importacao_erros' in request.session:
            del request.session['importacao_erros']
        if 'importacao_linhas_validas' in request.session:
            del request.session['importacao_linhas_validas']
        if 'importacao_linhas_invalidas' in request.session:
            del request.session['importacao_linhas_invalidas']
    
    if request.method == "POST":
        # Verificar se é AJAX
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        arquivo = request.FILES.get("arquivo")
        contrato_id = request.POST.get("contrato")
        
        if not arquivo:
            if is_ajax:
                return JsonResponse({'success': False, 'mensagem': 'Selecione um arquivo para importar.'})
            messages.error(request, "❌ Selecione um arquivo para importar.")
            return redirect("importar_veiculos")
        
        if not contrato_id:
            if is_ajax:
                return JsonResponse({'success': False, 'mensagem': 'Selecione um contrato.'})
            messages.error(request, "❌ Selecione um contrato.")
            return redirect("importar_veiculos")
        
        try:
            contrato = Contrato.objects.get(id=contrato_id)
        except Contrato.DoesNotExist:
            if is_ajax:
                return JsonResponse({'success': False, 'mensagem': 'Contrato não encontrado.'})
            messages.error(request, "❌ Contrato não encontrado.")
            return redirect("importar_veiculos")
        
        # Verificar extensão do arquivo
        if not arquivo.name.endswith(('.xlsx', '.xls')):
            if is_ajax:
                return JsonResponse({'success': False, 'mensagem': 'Formato de arquivo inválido. Use .xlsx ou .xls'})
            messages.error(request, "❌ Formato de arquivo inválido. Use .xlsx ou .xls")
            return redirect("importar_veiculos")
        
        # Ler o arquivo Excel
        try:
            df = pd.read_excel(arquivo)
        except Exception as e:
            if is_ajax:
                return JsonResponse({'success': False, 'mensagem': f'Erro ao ler o arquivo: {str(e)}'})
            messages.error(request, f"❌ Erro ao ler o arquivo: {str(e)}")
            return redirect("importar_veiculos")
        
        # Verificar se a planilha está vazia
        if df.empty:
            if is_ajax:
                return JsonResponse({'success': False, 'mensagem': 'A planilha está vazia.'})
            messages.error(request, "❌ A planilha está vazia.")
            return redirect("importar_veiculos")
        
        # PRÉ-VALIDAÇÃO: validar todos os registros antes de importar
        validacao = validar_importacao_veiculos(df, contrato)
        
        # Se houver erros, NÃO importa
        if validacao["erros"]:
            # Salvar erros na sessão
            request.session['importacao_erros'] = validacao["erros"]
            request.session['importacao_linhas_validas'] = validacao["linhas_validas"]
            request.session['importacao_linhas_invalidas'] = len(validacao["erros"])
            
            if is_ajax:
                return JsonResponse({
                    'success': False, 
                    'mensagem': f'{len(validacao["erros"])} erro(s) encontrados na planilha.',
                    'erros': validacao["erros"],
                    'recarregar': True
                })
            messages.error(request, f"❌ Importação cancelada! {len(validacao['erros'])} erro(s) encontrados.")
            return redirect("importar_veiculos")
        
        # Se passou na validação, processa a importação
        try:
            resultados = processar_importacao_veiculos_validada(df, contrato, request.user)
            
            # Limpar erros da sessão
            if 'importacao_erros' in request.session:
                del request.session['importacao_erros']
            if 'importacao_linhas_validas' in request.session:
                del request.session['importacao_linhas_validas']
            if 'importacao_linhas_invalidas' in request.session:
                del request.session['importacao_linhas_invalidas']
            
            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'criados': resultados['criados'],
                    'atualizados': resultados['atualizados'],
                    'total': resultados['total']
                })
            
            # Mensagem de sucesso (para requisições normais)
            if resultados["criados"] > 0 and resultados["atualizados"] > 0:
                messages.success(
                    request,
                    f"✅ Importação concluída! {resultados['criados']} veículos criados, "
                    f"{resultados['atualizados']} atualizados."
                )
            elif resultados["criados"] > 0:
                messages.success(request, f"✅ {resultados['criados']} veículos criados com sucesso.")
            elif resultados["atualizados"] > 0:
                messages.success(request, f"✅ {resultados['atualizados']} veículos atualizados com sucesso.")
            else:
                messages.warning(request, "⚠️ Nenhum registro foi processado.")
            
            return redirect("lista_veiculos")
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            
            if is_ajax:
                return JsonResponse({'success': False, 'mensagem': f'Erro na importação: {str(e)}'})
            messages.error(request, f"❌ Erro durante a importação: {str(e)}")
            return redirect("importar_veiculos")
    
    # 👈 IMPORTANTE: SEMPRE RETORNAR O RENDER PARA GET
    # GET - Mostrar formulário
    contratos = Contrato.objects.filter(ativo=True).order_by("nome")
    
    return render(request, "veiculos/importar.html", {
        "contratos": contratos,
    })




def processar_importacao_veiculos_validada(df, contrato, usuario):
    """
    Processa a importação APÓS validação bem-sucedida
    """
    
    resultados = {
        "criados": 0,
        "atualizados": 0,
        "total": 0,
        "erros": []
    }
    
    # Limpar nomes das colunas
    df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]
    
    for idx, row in df.iterrows():
        try:
            # ========== COLETAR E LIMPAR DADOS ==========
            
            # PLACA
            placa_raw = str(row.get("placa", "")).upper().strip()
            placa_valida, _ = validar_placa(placa_raw)
            if placa_valida:
                placa = formatar_placa(placa_raw)
            else:
                placa = placa_raw
            
            # RENAVAM
            renavam = None
            if pd.notna(row.get("renavam")) and str(row.get("renavam")).strip():
                renavam_raw = str(row.get("renavam")).strip()
                renavam = ''.join(filter(str.isdigit, renavam_raw))
            
            # TAG INTERNA
            tag_interna = None
            if pd.notna(row.get("tag_interna")) and str(row.get("tag_interna")).strip():
                tag_interna = str(row.get("tag_interna")).upper().strip()
                tag_interna = tag_interna.replace(" ", "")
            
            # DADOS BÁSICOS
            marca = str(row.get("marca", "")).strip()
            modelo = str(row.get("modelo", "")).strip()
            
            # ANO
            ano = 0
            if pd.notna(row.get("ano")):
                try:
                    ano = int(row.get("ano"))
                except:
                    ano = 0
            
            # COR
            cor = str(row.get("cor")) if pd.notna(row.get("cor")) else ""
            
            # KM ATUAL
            km_atual = 0
            if pd.notna(row.get("km_atual")):
                try:
                    km_atual = int(row.get("km_atual"))
                except:
                    km_atual = 0
            
            # TIPO E CATEGORIA
            tipo = str(row.get("tipo")) if pd.notna(row.get("tipo")) else "Carro"
            categoria = str(row.get("categoria")) if pd.notna(row.get("categoria")) else "Leve"
            combustivel = str(row.get("combustivel")) if pd.notna(row.get("combustivel")) else "Flex"
            tipo_propriedade = str(row.get("tipo_propriedade")) if pd.notna(row.get("tipo_propriedade")) else "Proprio"
            status = str(row.get("status")) if pd.notna(row.get("status")) else "Disponivel"
            
            # TAG CLIENTE
            tag_cliente = ""
            if pd.notna(row.get("tag_cliente")):
                tag_cliente = str(row.get("tag_cliente")).upper().strip()
            
            # DATAS
            ipva_vencimento = None
            if pd.notna(row.get("ipva_vencimento")):
                try:
                    ipva_vencimento = pd.to_datetime(row.get("ipva_vencimento")).date()
                except:
                    pass
            
            licenciamento_vencimento = None
            if pd.notna(row.get("licenciamento_vencimento")):
                try:
                    licenciamento_vencimento = pd.to_datetime(row.get("licenciamento_vencimento")).date()
                except:
                    pass
            
            seguro_validade = None
            if pd.notna(row.get("seguro_validade")):
                try:
                    seguro_validade = pd.to_datetime(row.get("seguro_validade")).date()
                except:
                    pass
            
            # SEGURO
            seguro = False
            if pd.notna(row.get("seguro")):
                valor = str(row.get("seguro")).lower().strip()
                seguro = valor in ["sim", "true", "1", "ok", "ativo", "yes"]
            
            # APOLICE E OBSERVAÇÕES
            apolice_numero = str(row.get("apolice_numero")) if pd.notna(row.get("apolice_numero")) else ""
            observacoes = str(row.get("observacoes")) if pd.notna(row.get("observacoes")) else ""
            
            # ========== VERIFICAR SE VEÍCULO JÁ EXISTE ==========
            veiculo_existente = Veiculo.objects.filter(placa=placa).first()
            
            if veiculo_existente:
                # Atualizar
                km_anterior = veiculo_existente.km_atual
                
                veiculo_existente.renavam = renavam
                veiculo_existente.marca = marca
                veiculo_existente.modelo = modelo
                veiculo_existente.ano = ano
                veiculo_existente.cor = cor
                veiculo_existente.contrato = contrato
                veiculo_existente.tag_interna = tag_interna
                veiculo_existente.tag_cliente = tag_cliente
                veiculo_existente.tipo = tipo
                veiculo_existente.categoria = categoria
                veiculo_existente.combustivel = combustivel
                veiculo_existente.km_atual = km_atual
                veiculo_existente.tipo_propriedade = tipo_propriedade
                veiculo_existente.status = status
                veiculo_existente.ativo = True
                veiculo_existente.ipva_vencimento = ipva_vencimento
                veiculo_existente.licenciamento_vencimento = licenciamento_vencimento
                veiculo_existente.seguro = seguro
                veiculo_existente.seguro_validade = seguro_validade
                veiculo_existente.apolice_numero = apolice_numero
                veiculo_existente.observacoes = observacoes
                
                veiculo_existente.save()
                
                # Registrar histórico de KM
                if km_atual > 0 and km_anterior != km_atual:
                    HistoricoKM.objects.create(
                        veiculo=veiculo_existente,
                        km_anterior=km_anterior,
                        km_novo=km_atual,
                        origem="IMPORTACAO"
                    )
                
                resultados["atualizados"] += 1
            else:
                # Criar novo
                veiculo = Veiculo(
                    placa=placa,
                    renavam=renavam,
                    marca=marca,
                    modelo=modelo,
                    ano=ano,
                    cor=cor,
                    contrato=contrato,
                    tag_interna=tag_interna,
                    tag_cliente=tag_cliente,
                    tipo=tipo,
                    categoria=categoria,
                    combustivel=combustivel,
                    km_atual=km_atual,
                    tipo_propriedade=tipo_propriedade,
                    status=status,
                    ativo=True,
                    origem='IMPORTACAO',
                    ipva_vencimento=ipva_vencimento,
                    licenciamento_vencimento=licenciamento_vencimento,
                    seguro=seguro,
                    seguro_validade=seguro_validade,
                    apolice_numero=apolice_numero,
                    observacoes=observacoes
                )
                
                veiculo.save()
                
                # Registrar histórico de KM inicial
                if km_atual > 0:
                    HistoricoKM.objects.create(
                        veiculo=veiculo,
                        km_anterior=0,
                        km_novo=km_atual,
                        origem="IMPORTACAO"
                    )
                
                resultados["criados"] += 1
            
            resultados["total"] += 1
                
        except Exception as e:
            resultados["erros"].append(f"Linha {idx+2}: {str(e)}")
            import traceback
            traceback.print_exc()
    
    return resultados
    """View para importar veículos via Excel com pré-validação"""
    
    perfil = request.user.perfilusuario
    
    # Verificar se é ADM
    if perfil.nivel != "adm":
        messages.error(request, "Apenas administradores podem importar dados.")
        return redirect("lista_veiculos")
    
    if request.method == "POST":
        arquivo = request.FILES.get("arquivo")
        contrato_id = request.POST.get("contrato")
        
        if not arquivo:
            messages.error(request, "❌ Selecione um arquivo para importar.")
            return redirect("importar_veiculos")
        
        if not contrato_id:
            messages.error(request, "❌ Selecione um contrato.")
            return redirect("importar_veiculos")
        
        try:
            contrato = Contrato.objects.get(id=contrato_id)
        except Contrato.DoesNotExist:
            messages.error(request, "❌ Contrato não encontrado.")
            return redirect("importar_veiculos")
        
        # Verificar extensão do arquivo
        if not arquivo.name.endswith(('.xlsx', '.xls')):
            messages.error(request, "❌ Formato de arquivo inválido. Use .xlsx ou .xls")
            return redirect("importar_veiculos")
        
        # Ler o arquivo Excel
        try:
            df = pd.read_excel(arquivo)
        except Exception as e:
            messages.error(request, f"❌ Erro ao ler o arquivo: {str(e)}")
            return redirect("importar_veiculos")
        
        # Verificar se a planilha está vazia
        if df.empty:
            messages.error(request, "❌ A planilha está vazia.")
            return redirect("importar_veiculos")
        
        # PRÉ-VALIDAÇÃO: validar todos os registros antes de importar
        validacao = validar_importacao_veiculos(df, contrato)
        
        # Se houver erros, NÃO importa e volta com erros na sessão
        if validacao["erros"]:
            # Salvar erros na sessão para exibir na tela de importação
            request.session['importacao_erros'] = validacao["erros"]
            request.session['importacao_linhas_validas'] = validacao["linhas_validas"]
            request.session['importacao_linhas_invalidas'] = len(validacao["erros"])
            
            messages.error(
                request, 
                f"❌ Importação cancelada! {len(validacao['erros'])} erro(s) encontrados."
            )
            return redirect("importar_veiculos")  # Volta para tela de importação com erros
        
        # Se passou na validação, processa a importação
        try:
            resultados = processar_importacao_veiculos_validada(df, contrato, request.user)
            
            # Mensagem de sucesso
            if resultados["criados"] > 0 and resultados["atualizados"] > 0:
                messages.success(
                    request,
                    f"✅ Importação concluída! {resultados['criados']} veículos criados, "
                    f"{resultados['atualizados']} atualizados. Total: {resultados['total']} registros."
                )
            elif resultados["criados"] > 0:
                messages.success(
                    request,
                    f"✅ Importação concluída! {resultados['criados']} veículos criados com sucesso."
                )
            elif resultados["atualizados"] > 0:
                messages.success(
                    request,
                    f"✅ Importação concluída! {resultados['atualizados']} veículos atualizados com sucesso."
                )
            else:
                messages.warning(request, "⚠️ Nenhum registro foi processado.")
            
            # Limpar erros da sessão
            if 'importacao_erros' in request.session:
                del request.session['importacao_erros']
            if 'importacao_linhas_validas' in request.session:
                del request.session['importacao_linhas_validas']
            if 'importacao_linhas_invalidas' in request.session:
                del request.session['importacao_linhas_invalidas']
            
        except Exception as e:
            messages.error(request, f"❌ Erro durante a importação: {str(e)}")
            import traceback
            traceback.print_exc()
            return redirect("importar_veiculos")
        
        # REDIRECIONA PARA LISTA COM MENSAGEM DE SUCESSO
        return redirect("lista_veiculos")
    
    # GET - Mostrar formulário
    contratos = Contrato.objects.filter(ativo=True).order_by("nome")
    
    return render(request, "veiculos/importar.html", {
        "contratos": contratos,
    })


def validar_importacao_veiculos(df, contrato):
    """
    Valida todos os registros antes da importação.
    Retorna dicionário com erros detalhados.
    """
    
    resultado = {
        "erros": [],
        "linhas_validas": 0,
        "linhas_invalidas": 0
    }
    
    # Conjuntos para verificar duplicidades NA MESMA PLANILHA
    placas_planilha = {}
    renavams_planilha = {}
    tags_planilha = {}
    
    # Limpar nomes das colunas
    df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]
    
    # Verificar colunas obrigatórias
    colunas_obrigatorias = ['placa', 'marca', 'modelo']
    colunas_faltando = [col for col in colunas_obrigatorias if col not in df.columns]
    
    if colunas_faltando:
        resultado["erros"].append({
            "linha": "CABEÇALHO",
            "campo": ", ".join(colunas_faltando),
            "erro": f"Colunas obrigatórias faltando: {', '.join(colunas_faltando)}"
        })
        return resultado
    
    # Buscar todos os registros existentes no banco (para validação de unicidade)
    veiculos_existentes = Veiculo.objects.all()
    renavams_existentes = {v.renavam: v for v in veiculos_existentes if v.renavam}
    tags_existentes = {v.tag_interna: v for v in veiculos_existentes if v.tag_interna}
    
    for idx, row in df.iterrows():
        numero_linha = idx + 2  # +2 porque o cabeçalho é linha 1
        erros_linha = []  # 👈 INICIALIZAR AQUI
        placa = None  # Inicializar placa
        
        try:
            # ========== VALIDAÇÃO DA PLACA ==========
            placa_raw = str(row.get("placa", "")).upper().strip()
            if not placa_raw:
                erros_linha.append("Placa é obrigatória")
            else:
                placa_valida, placa_msg = validar_placa(placa_raw)
                if not placa_valida:
                    erros_linha.append(placa_msg)
                else:
                    placa = formatar_placa(placa_raw)
                    tipo_placa = obter_tipo_placa(placa)
                    
                    # Verificar duplicidade na planilha
                    if placa in placas_planilha:
                        erros_linha.append(f"Placa '{placa}' duplicada na planilha (linha {placas_planilha[placa]})")
                    else:
                        placas_planilha[placa] = numero_linha
                    
                    # Opcional: registrar tipo de placa
                    if tipo_placa == "mercosul":
                        pass
            
            # ========== VALIDAÇÃO DO RENAVAM ==========
            renavam_raw = row.get("renavam", "")
            renavam = None
            if pd.notna(renavam_raw) and str(renavam_raw).strip():
                renavam_original = str(renavam_raw).strip()
                renavam_limpo = ''.join(filter(str.isdigit, renavam_original))
                
                if not renavam_limpo:
                    erros_linha.append(f"Renavam '{renavam_original}' inválido (deve conter apenas números)")
                elif len(renavam_limpo) not in [9, 11]:
                    erros_linha.append(f"Renavam deve ter 9 ou 11 dígitos (recebido: {len(renavam_limpo)})")
                else:
                    renavam = renavam_limpo
                    
                    # Verificar duplicidade na planilha
                    if renavam in renavams_planilha:
                        erros_linha.append(f"Renavam '{renavam}' duplicado na planilha (linha {renavams_planilha[renavam]})")
                    else:
                        renavams_planilha[renavam] = numero_linha
                    
                    # Verificar se já existe no banco (se for um veículo diferente)
                    if renavam in renavams_existentes and placa:
                        veiculo_existente = renavams_existentes[renavam]
                        if veiculo_existente.placa != placa:
                            erros_linha.append(f"Renavam '{renavam}' já cadastrado para o veículo {veiculo_existente.placa}")
            
            # ========== VALIDAÇÃO DA TAG INTERNA ==========
            tag_raw = row.get("tag_interna", "")
            tag_interna = None
            if pd.notna(tag_raw) and str(tag_raw).strip():
                tag_interna = str(tag_raw).upper().strip()
                
                # Validar formato
                if not re.match(r'^[A-Z]{2}-\d{3,4}$', tag_interna):
                    erros_linha.append(f"Tag interna '{tag_interna}' inválida. Formato sugerido: VA-100")
                else:
                    # Verificar duplicidade na planilha
                    if tag_interna in tags_planilha:
                        erros_linha.append(f"Tag interna '{tag_interna}' duplicada na planilha (linha {tags_planilha[tag_interna]})")
                    else:
                        tags_planilha[tag_interna] = numero_linha
                    
                    # Verificar se já existe no banco (se for um veículo diferente)
                    if tag_interna in tags_existentes and placa:
                        veiculo_existente = tags_existentes[tag_interna]
                        if veiculo_existente.placa != placa:
                            erros_linha.append(f"Tag interna '{tag_interna}' já cadastrada para o veículo {veiculo_existente.placa}")
            
            # ========== VALIDAÇÃO MARCA E MODELO ==========
            marca = str(row.get("marca", "")).strip()
            if not marca:
                erros_linha.append("Marca é obrigatória")
            
            modelo = str(row.get("modelo", "")).strip()
            if not modelo:
                erros_linha.append("Modelo é obrigatório")
            
            # ========== VALIDAÇÃO DO ANO ==========
            ano = row.get("ano")
            if pd.notna(ano):
                try:
                    ano_int = int(ano)
                    from datetime import date
                    ano_atual = date.today().year
                    if ano_int < 1900 or ano_int > ano_atual + 1:
                        erros_linha.append(f"Ano '{ano}' inválido (deve estar entre 1900 e {ano_atual + 1})")
                except:
                    erros_linha.append(f"Ano '{ano}' inválido (deve ser um número)")
            
            # ========== VALIDAÇÃO DO KM ==========
            km = row.get("km_atual")
            if pd.notna(km):
                try:
                    km_int = int(km)
                    if km_int < 0:
                        erros_linha.append(f"KM não pode ser negativo")
                except:
                    erros_linha.append(f"KM '{km}' inválido (deve ser um número)")
            
            # ========== VALIDAÇÃO DE STATUS ==========
            status = str(row.get("status", "")).strip() if pd.notna(row.get("status")) else "Disponivel"
            status_validos = ["Disponivel", "EmTransito", "Manutencao", "Reservado"]
            if status not in status_validos:
                erros_linha.append(f"Status '{status}' inválido. Opções: {', '.join(status_validos)}")
            
        except Exception as e:
            erros_linha.append(f"Erro inesperado: {str(e)}")
        
        # Registrar erros da linha
        if erros_linha:  # 👈 AGORA A VARIÁVEL SEMPRE EXISTE
            resultado["linhas_invalidas"] += 1
            resultado["erros"].append({
                "linha": numero_linha,
                "placa": placa if placa else (placa_raw if 'placa_raw' in locals() else "N/A"),
                "erros": erros_linha
            })
        else:
            resultado["linhas_validas"] += 1
    
    return resultado


def processar_importacao_veiculos_validada(df, contrato, usuario):
    """
    Processa a importação APÓS validação bem-sucedida
    """
    
    resultados = {
        "criados": 0,
        "atualizados": 0,
        "total": 0,
        "erros": []
    }
    
    # Limpar nomes das colunas
    df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]
    
    for idx, row in df.iterrows():
        try:
            # ========== COLETAR E LIMPAR DADOS ==========
            
            # PLACA - validar e formatar
            placa_raw = str(row.get("placa", "")).upper().strip()
            placa_valida, _ = validar_placa(placa_raw)
            if placa_valida:
                placa = formatar_placa(placa_raw)
            else:
                placa = placa_raw  # fallback (não deve ocorrer pois já foi validado)
            
            # RENAVAM
            renavam = None
            if pd.notna(row.get("renavam")) and str(row.get("renavam")).strip():
                renavam_raw = str(row.get("renavam")).strip()
                renavam = ''.join(filter(str.isdigit, renavam_raw))
            
            # TAG INTERNA
            tag_interna = None
            if pd.notna(row.get("tag_interna")) and str(row.get("tag_interna")).strip():
                tag_interna = str(row.get("tag_interna")).upper().strip()
                # Remover possíveis espaços extras
                tag_interna = tag_interna.replace(" ", "")
            
            # DADOS BÁSICOS
            marca = str(row.get("marca", "")).strip()
            modelo = str(row.get("modelo", "")).strip()
            
            # ANO
            ano = 0
            if pd.notna(row.get("ano")):
                try:
                    ano = int(row.get("ano"))
                except:
                    ano = 0
            
            # COR
            cor = str(row.get("cor")) if pd.notna(row.get("cor")) else ""
            
            # KM ATUAL
            km_atual = 0
            if pd.notna(row.get("km_atual")):
                try:
                    km_atual = int(row.get("km_atual"))
                except:
                    km_atual = 0
            
            # TIPO E CATEGORIA
            tipo = str(row.get("tipo")) if pd.notna(row.get("tipo")) else "Carro"
            categoria = str(row.get("categoria")) if pd.notna(row.get("categoria")) else "Leve"
            combustivel = str(row.get("combustivel")) if pd.notna(row.get("combustivel")) else "Flex"
            tipo_propriedade = str(row.get("tipo_propriedade")) if pd.notna(row.get("tipo_propriedade")) else "Proprio"
            status = str(row.get("status")) if pd.notna(row.get("status")) else "Disponivel"
            
            # TAG CLIENTE
            tag_cliente = ""
            if pd.notna(row.get("tag_cliente")):
                tag_cliente = str(row.get("tag_cliente")).upper().strip()
            
            # DATAS
            ipva_vencimento = None
            if pd.notna(row.get("ipva_vencimento")):
                try:
                    ipva_vencimento = pd.to_datetime(row.get("ipva_vencimento")).date()
                except:
                    pass
            
            licenciamento_vencimento = None
            if pd.notna(row.get("licenciamento_vencimento")):
                try:
                    licenciamento_vencimento = pd.to_datetime(row.get("licenciamento_vencimento")).date()
                except:
                    pass
            
            seguro_validade = None
            if pd.notna(row.get("seguro_validade")):
                try:
                    seguro_validade = pd.to_datetime(row.get("seguro_validade")).date()
                except:
                    pass
            
            # SEGURO (booleano)
            seguro = False
            if pd.notna(row.get("seguro")):
                valor = str(row.get("seguro")).lower().strip()
                seguro = valor in ["sim", "true", "1", "ok", "ativo", "yes"]
            
            # APOLICE E OBSERVAÇÕES
            apolice_numero = str(row.get("apolice_numero")) if pd.notna(row.get("apolice_numero")) else ""
            observacoes = str(row.get("observacoes")) if pd.notna(row.get("observacoes")) else ""
            
            # ========== VERIFICAR SE VEÍCULO JÁ EXISTE ==========
            veiculo_existente = Veiculo.objects.filter(placa=placa).first()
            
            if veiculo_existente:
                # ========== ATUALIZAR VEÍCULO EXISTENTE ==========
                km_anterior = veiculo_existente.km_atual
                
                veiculo_existente.renavam = renavam
                veiculo_existente.marca = marca
                veiculo_existente.modelo = modelo
                veiculo_existente.ano = ano
                veiculo_existente.cor = cor
                veiculo_existente.contrato = contrato
                veiculo_existente.tag_interna = tag_interna
                veiculo_existente.tag_cliente = tag_cliente
                veiculo_existente.tipo = tipo
                veiculo_existente.categoria = categoria
                veiculo_existente.combustivel = combustivel
                veiculo_existente.km_atual = km_atual
                veiculo_existente.tipo_propriedade = tipo_propriedade
                veiculo_existente.status = status
                veiculo_existente.ativo = True
                veiculo_existente.ipva_vencimento = ipva_vencimento
                veiculo_existente.licenciamento_vencimento = licenciamento_vencimento
                veiculo_existente.seguro = seguro
                veiculo_existente.seguro_validade = seguro_validade
                veiculo_existente.apolice_numero = apolice_numero
                veiculo_existente.observacoes = observacoes
                
                veiculo_existente.save()
                
                # Registrar histórico de KM se houve alteração
                if km_atual > 0 and km_anterior != km_atual:
                    HistoricoKM.objects.create(
                        veiculo=veiculo_existente,
                        km_anterior=km_anterior,
                        km_novo=km_atual,
                        origem="IMPORTACAO"
                    )
                
                resultados["atualizados"] += 1
                
            else:
                # ========== CRIAR NOVO VEÍCULO ==========
                veiculo = Veiculo(
                    placa=placa,
                    renavam=renavam,
                    marca=marca,
                    modelo=modelo,
                    ano=ano,
                    cor=cor,
                    contrato=contrato,
                    tag_interna=tag_interna,
                    tag_cliente=tag_cliente,
                    tipo=tipo,
                    categoria=categoria,
                    combustivel=combustivel,
                    km_atual=km_atual,
                    tipo_propriedade=tipo_propriedade,
                    status=status,
                    ativo=True,
                    origem='IMPORTACAO',
                    ipva_vencimento=ipva_vencimento,
                    licenciamento_vencimento=licenciamento_vencimento,
                    seguro=seguro,
                    seguro_validade=seguro_validade,
                    apolice_numero=apolice_numero,
                    observacoes=observacoes
                )
                
                veiculo.save()
                
                # Registrar histórico de KM inicial
                if km_atual > 0:
                    HistoricoKM.objects.create(
                        veiculo=veiculo,
                        km_anterior=0,
                        km_novo=km_atual,
                        origem="IMPORTACAO"
                    )
                
                resultados["criados"] += 1
            
            resultados["total"] += 1
                
        except Exception as e:
            resultados["erros"].append(f"Linha {idx+2}: {str(e)}")
            print(f"Erro na linha {idx+2}: {str(e)}")
            import traceback
            traceback.print_exc()
    
    return resultados





# Função para processar a importação com validações 
def processar_importacao_veiculos(df, contrato, usuario):
    """Processa a importação dos veículos com validações"""
    
    resultados = {
        "criados": 0,
        "atualizados": 0,
        "erros": []
    }
    
    # Conjuntos para verificar duplicidades na mesma importação
    placas_importadas = set()
    renavams_importados = set()
    tags_importadas = set()
    
    # Limpar nomes das colunas
    df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]
    
    # Verificar colunas obrigatórias
    colunas_obrigatorias = ['placa', 'marca', 'modelo']
    colunas_faltando = [col for col in colunas_obrigatorias if col not in df.columns]
    
    if colunas_faltando:
        resultados["erros"].append(f"Colunas obrigatórias faltando: {', '.join(colunas_faltando)}")
        return resultados
    
    for idx, row in df.iterrows():
        try:
            # ========== VALIDAÇÃO DA PLACA ==========
            placa = str(row.get("placa", "")).upper().strip()
            if not placa:
                resultados["erros"].append(f"Linha {idx+2}: Placa é obrigatória")
                continue
            
            # Validar formato da placa (ABC-1234)
            import re
            if not re.match(r'^[A-Z]{3}-\d{4}$', placa):
                resultados["erros"].append(f"Linha {idx+2}: Placa '{placa}' inválida. Formato correto: ABC-1234")
                continue
            
            # Verificar placa duplicada na mesma importação
            if placa in placas_importadas:
                resultados["erros"].append(f"Linha {idx+2}: Placa '{placa}' duplicada na planilha")
                continue
            placas_importadas.add(placa)
            
            # ========== VALIDAÇÃO DO RENAVAM ==========
            renavam = str(row.get("renavam", "")).strip() if pd.notna(row.get("renavam")) else ""
            if renavam:
                # Limpar renavam (apenas números)
                renavam_limpo = ''.join(filter(str.isdigit, renavam))
                if not renavam_limpo:
                    resultados["erros"].append(f"Linha {idx+2}: Renavam '{renavam}' inválido (deve conter apenas números)")
                    continue
                if len(renavam_limpo) not in [9, 11]:
                    resultados["erros"].append(f"Linha {idx+2}: Renavam deve ter 9 ou 11 dígitos")
                    continue
                
                # Verificar renavam duplicado na mesma importação
                if renavam_limpo in renavams_importados:
                    resultados["erros"].append(f"Linha {idx+2}: Renavam '{renavam}' duplicado na planilha")
                    continue
                renavams_importados.add(renavam_limpo)
                renavam = renavam_limpo
            else:
                renavam = None
            
            # ========== VALIDAÇÃO DA TAG INTERNA ==========
            tag_interna = str(row.get("tag_interna", "")).upper().strip() if pd.notna(row.get("tag_interna")) else ""
            if tag_interna:
                # Verificar formato da tag (opcional, pode ser ajustado)
                # Exemplo: VA-100, VA-101, etc
                if not re.match(r'^[A-Z]{2}-\d{3,4}$', tag_interna):
                    resultados["erros"].append(f"Linha {idx+2}: Tag interna '{tag_interna}' inválida. Formato sugerido: VA-100")
                    continue
                
                # Verificar tag duplicada na mesma importação
                if tag_interna in tags_importadas:
                    resultados["erros"].append(f"Linha {idx+2}: Tag interna '{tag_interna}' duplicada na planilha")
                    continue
                tags_importadas.add(tag_interna)
            
            # ========== VALIDAÇÃO MARCA E MODELO ==========
            marca = str(row.get("marca", "")).strip()
            modelo = str(row.get("modelo", "")).strip()
            
            if not marca:
                resultados["erros"].append(f"Linha {idx+2}: Marca é obrigatória")
                continue
            
            if not modelo:
                resultados["erros"].append(f"Linha {idx+2}: Modelo é obrigatório")
                continue
            
            # ========== VALIDAÇÃO DO ANO ==========
            ano = row.get("ano")
            if pd.notna(ano):
                try:
                    ano = int(ano)
                    from datetime import date
                    ano_atual = date.today().year
                    if ano < 1900 or ano > ano_atual + 1:
                        resultados["erros"].append(f"Linha {idx+2}: Ano '{ano}' inválido (deve estar entre 1900 e {ano_atual + 1})")
                        continue
                except:
                    resultados["erros"].append(f"Linha {idx+2}: Ano inválido")
                    continue
            else:
                ano = 0
            
            # ========== VALIDAÇÃO DO KM ==========
            km_atual = 0
            if pd.notna(row.get("km_atual")):
                try:
                    km_atual = int(row.get("km_atual"))
                    if km_atual < 0:
                        resultados["erros"].append(f"Linha {idx+2}: KM não pode ser negativo")
                        continue
                except:
                    resultados["erros"].append(f"Linha {idx+2}: KM inválido")
                    continue
            
            # ========== VERIFICAR SE JÁ EXISTE NO BANCO ==========
            # Verificar placa existente
            veiculo_existente = Veiculo.objects.filter(placa=placa).first()
            
            if veiculo_existente:
                # Verificar renavam duplicado (exceto o próprio veículo)
                if renavam and Veiculo.objects.filter(renavam=renavam).exclude(pk=veiculo_existente.pk).exists():
                    resultados["erros"].append(f"Linha {idx+2}: Renavam '{renavam}' já cadastrado para outro veículo")
                    continue
                
                # Verificar tag interna duplicada (exceto o próprio veículo)
                if tag_interna and Veiculo.objects.filter(tag_interna=tag_interna).exclude(pk=veiculo_existente.pk).exists():
                    resultados["erros"].append(f"Linha {idx+2}: Tag interna '{tag_interna}' já cadastrada para outro veículo")
                    continue
                
                # Atualizar veículo existente
                km_anterior = veiculo_existente.km_atual
                
                veiculo_existente.marca = marca
                veiculo_existente.modelo = modelo
                veiculo_existente.ano = ano
                veiculo_existente.cor = str(row.get("cor")) if pd.notna(row.get("cor")) else ""
                veiculo_existente.contrato = contrato
                veiculo_existente.tag_interna = tag_interna
                veiculo_existente.tag_cliente = str(row.get("tag_cliente")).upper() if pd.notna(row.get("tag_cliente")) else ""
                veiculo_existente.tipo = str(row.get("tipo")) if pd.notna(row.get("tipo")) else "Carro"
                veiculo_existente.categoria = str(row.get("categoria")) if pd.notna(row.get("categoria")) else "Leve"
                veiculo_existente.combustivel = str(row.get("combustivel")) if pd.notna(row.get("combustivel")) else "Flex"
                veiculo_existente.km_atual = km_atual
                veiculo_existente.tipo_propriedade = str(row.get("tipo_propriedade")) if pd.notna(row.get("tipo_propriedade")) else "Proprio"
                veiculo_existente.status = str(row.get("status")) if pd.notna(row.get("status")) else "Disponivel"
                veiculo_existente.ativo = True
                
                # Tratar datas
                if pd.notna(row.get("ipva_vencimento")):
                    try:
                        veiculo_existente.ipva_vencimento = pd.to_datetime(row.get("ipva_vencimento")).date()
                    except:
                        pass
                
                if pd.notna(row.get("licenciamento_vencimento")):
                    try:
                        veiculo_existente.licenciamento_vencimento = pd.to_datetime(row.get("licenciamento_vencimento")).date()
                    except:
                        pass
                
                seguro = False
                if pd.notna(row.get("seguro")):
                    valor = str(row.get("seguro")).lower().strip()
                    seguro = valor in ["sim", "true", "1", "ok", "ativo", "yes"]
                veiculo_existente.seguro = seguro
                
                if pd.notna(row.get("seguro_validade")):
                    try:
                        veiculo_existente.seguro_validade = pd.to_datetime(row.get("seguro_validade")).date()
                    except:
                        pass
                
                veiculo_existente.apolice_numero = str(row.get("apolice_numero")) if pd.notna(row.get("apolice_numero")) else ""
                veiculo_existente.observacoes = str(row.get("observacoes")) if pd.notna(row.get("observacoes")) else ""
                
                # Atualizar renavam se veio na planilha
                if renavam:
                    veiculo_existente.renavam = renavam
                
                veiculo_existente.save()
                
                # Registrar histórico de KM se houve alteração
                if km_atual > 0 and km_anterior != km_atual:
                    HistoricoKM.objects.create(
                        veiculo=veiculo_existente,
                        km_anterior=km_anterior,
                        km_novo=km_atual,
                        origem="IMPORTACAO"
                    )
                
                resultados["atualizados"] += 1
                continue
            
            # ========== CRIAR NOVO VEÍCULO ==========
            # Verificar renavam já existe
            if renavam and Veiculo.objects.filter(renavam=renavam).exists():
                resultados["erros"].append(f"Linha {idx+2}: Renavam '{renavam}' já cadastrado para outro veículo")
                continue
            
            # Verificar tag interna já existe
            if tag_interna and Veiculo.objects.filter(tag_interna=tag_interna).exists():
                resultados["erros"].append(f"Linha {idx+2}: Tag interna '{tag_interna}' já cadastrada para outro veículo")
                continue
            
            # Criar novo veículo
            veiculo = Veiculo(
                placa=placa,
                renavam=renavam,
                marca=marca,
                modelo=modelo,
                ano=ano,
                cor=str(row.get("cor")) if pd.notna(row.get("cor")) else "",
                contrato=contrato,
                tag_interna=tag_interna,
                tag_cliente=str(row.get("tag_cliente")).upper() if pd.notna(row.get("tag_cliente")) else "",
                tipo=str(row.get("tipo")) if pd.notna(row.get("tipo")) else "Carro",
                categoria=str(row.get("categoria")) if pd.notna(row.get("categoria")) else "Leve",
                combustivel=str(row.get("combustivel")) if pd.notna(row.get("combustivel")) else "Flex",
                km_atual=km_atual,
                tipo_propriedade=str(row.get("tipo_propriedade")) if pd.notna(row.get("tipo_propriedade")) else "Proprio",
                status=str(row.get("status")) if pd.notna(row.get("status")) else "Disponivel",
                ativo=True,
                origem='IMPORTACAO'
            )
            
            # Tratar datas
            if pd.notna(row.get("ipva_vencimento")):
                try:
                    veiculo.ipva_vencimento = pd.to_datetime(row.get("ipva_vencimento")).date()
                except:
                    pass
            
            if pd.notna(row.get("licenciamento_vencimento")):
                try:
                    veiculo.licenciamento_vencimento = pd.to_datetime(row.get("licenciamento_vencimento")).date()
                except:
                    pass
            
            seguro = False
            if pd.notna(row.get("seguro")):
                valor = str(row.get("seguro")).lower().strip()
                seguro = valor in ["sim", "true", "1", "ok", "ativo", "yes"]
            veiculo.seguro = seguro
            
            if pd.notna(row.get("seguro_validade")):
                try:
                    veiculo.seguro_validade = pd.to_datetime(row.get("seguro_validade")).date()
                except:
                    pass
            
            veiculo.apolice_numero = str(row.get("apolice_numero")) if pd.notna(row.get("apolice_numero")) else ""
            veiculo.observacoes = str(row.get("observacoes")) if pd.notna(row.get("observacoes")) else ""
            
            veiculo.save()
            
            # Registrar histórico de KM inicial
            if km_atual > 0:
                HistoricoKM.objects.create(
                    veiculo=veiculo,
                    km_anterior=0,
                    km_novo=km_atual,
                    origem="IMPORTACAO"
                )
            
            resultados["criados"] += 1
                
        except Exception as e:
            resultados["erros"].append(f"Linha {idx+2}: {str(e)}")
            print(traceback.format_exc())
    
    return resultados


def baixar_modelo_veiculos(request):
    """Baixa modelo de planilha para veículos"""
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Veículos"
    
    # Cabeçalhos
    headers = [
        "placa", "renavam", "marca", "modelo", "ano", "cor",
        "tag_interna", "tag_cliente", "tipo", "categoria",
        "combustivel", "km_atual", "tipo_propriedade", "status",
        "ipva_vencimento", "licenciamento_vencimento", "seguro",
        "seguro_validade", "apolice_numero", "observacoes"
    ]
    
    # Estilo do cabeçalho
    header_fill = PatternFill(start_color="00594C", end_color="00594C", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)
    header_alignment = Alignment(horizontal="center")
    
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = header_alignment
    
    # Dados de exemplo
    exemplos = [
        ["OTE-7884", "12345678901", "TOYOTA", "HILUX 3.0 4X4", 2023, "BRANCA",
         "VA-100", "", "Utilitario", "Leve", "Diesel", 75000, "Proprio", "Disponivel",
         "31/12/2025", "31/12/2025", "Sim", "31/12/2025", "AP-123456", ""],
        ["GAV-895", "98765432109", "FIAT", "TITANO 2.0", 2022, "PRATA",
         "VA-101", "", "Utilitario", "Leve", "Diesel", 45000, "Proprio", "Disponivel",
         "31/12/2025", "31/12/2025", "Sim", "31/12/2025", "AP-789012", ""],
        ["DFR-8425", "45678912345", "FORD", "RANGER 2.2 XLS", 2024, "PRETA",
         "VA-102", "", "Utilitario", "Leve", "Diesel", 12000, "Locado", "Disponivel",
         "31/12/2026", "31/12/2026", "Sim", "31/12/2026", "AP-345678", ""],
    ]
    
    for row_idx, exemplo in enumerate(exemplos, 2):
        for col_idx, valor in enumerate(exemplo, 1):
            ws.cell(row=row_idx, column=col_idx, value=valor)
    
    # Ajustar largura das colunas
    for col in ws.columns:
        max_length = 0
        col_letter = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        ws.column_dimensions[col_letter].width = min(max_length + 2, 30)
    
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="modelo_veiculos.xlsx"'
    wb.save(response)
    return response