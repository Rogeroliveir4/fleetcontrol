from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.db.models import Q
from datetime import date as dt_date, timedelta  # Renomeado para evitar conflito
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

from .models import Motorista
from contratos.models import Contrato
from contas.models import PerfilUsuario
from datetime import date


# ----------------------------------------------------------------------
# LISTA MOTORISTAS (com filtro por contrato do usuário)
# ----------------------------------------------------------------------
def lista_motoristas(request):
    perfil = request.user.perfilusuario  # PerfilUsuario com contrato FK

    status = request.GET.get("status") or "ativo"
    busca = request.GET.get("search")

    # Base
    motoristas = Motorista.objects.all()

    # 🔥 Filtrar por contrato se não for ADMIN
    if perfil.nivel != "adm" and perfil.contrato_id:
        motoristas = motoristas.filter(contrato_id=perfil.contrato_id)

    # Filtro por status
    if status == "ativo":
        motoristas = motoristas.filter(ativo=True)
    elif status == "inativo":
        motoristas = motoristas.filter(ativo=False)
    elif status == "vencimento":
        limite = dt_date.today() + timedelta(days=60)  # Usando dt_date em vez de date
        motoristas = motoristas.filter(
            cnh_vencimento__lte=limite,
            ativo=True
        )

    # Busca inteligente
    if busca:
        motoristas = motoristas.filter(
            Q(nome__icontains=busca) |
            Q(cpf__icontains=busca) |
            Q(telefone__icontains=busca) |
            Q(cnh_numero__icontains=busca) |
            Q(cnh_categoria__icontains=busca)
        )

    # Calcular estatísticas
    motoristas_ativos = Motorista.objects.filter(ativo=True)
    motoristas_inativos = Motorista.objects.filter(ativo=False)
    
    # Aplicar filtro de contrato nas estatísticas também
    if perfil.nivel != "adm" and perfil.contrato_id:
        motoristas_ativos = motoristas_ativos.filter(contrato_id=perfil.contrato_id)
        motoristas_inativos = motoristas_inativos.filter(contrato_id=perfil.contrato_id)
    
    motoristas_ativos_count = motoristas_ativos.count()
    motoristas_inativos_count = motoristas_inativos.count()
    
    # Calcular vencimentos (60 dias)
    limite_vencimento = dt_date.today() + timedelta(days=60)
    motoristas_vencendo = Motorista.objects.filter(
        cnh_vencimento__lte=limite_vencimento,
        ativo=True
    )
    
    # Aplicar filtro de contrato nos vencimentos também
    if perfil.nivel != "adm" and perfil.contrato_id:
        motoristas_vencendo = motoristas_vencendo.filter(contrato_id=perfil.contrato_id)
    
    motoristas_vencendo_count = motoristas_vencendo.count()

    return render(request, "motoristas/lista.html", {
        "motoristas": motoristas,
        "motoristas_ativos": motoristas_ativos_count,
        "motoristas_inativos": motoristas_inativos_count,
        "motoristas_vencendo": motoristas_vencendo_count,
        "status": status,
        "search": busca
    })


# ----------------------------------------------------------------------
# CRIAR MOTORISTA (agora com combobox de contratos)
# ----------------------------------------------------------------------
def criar_motorista(request):
    # Buscar todos os contratos ativos para o combobox
    contratos = Contrato.objects.filter(ativo=True).order_by('nome')
    
    if request.method == "POST":
        # O campo agora é "contrato" (select) ao invés de "id_contrato"
        contrato_id = request.POST.get("contrato")
        contrato_obj = Contrato.objects.filter(id=contrato_id).first() if contrato_id else None
        
        # O campo ativo agora vem como "True"/"False" string
        ativo = request.POST.get("ativo") == "True"

        Motorista.objects.create(
            nome=request.POST["nome"],
            cpf=request.POST["cpf"],
            telefone=request.POST["telefone"],
            cnh_numero=request.POST["cnh_numero"],
            cnh_categoria=request.POST["cnh_categoria"],
            cnh_vencimento=request.POST["cnh_vencimento"],
            ativo=ativo,
            contrato=contrato_obj
        )

        return redirect("lista_motoristas")

    return render(request, "motoristas/form.html", {
        "contratos": contratos,
        "motorista": None
    })


# ----------------------------------------------------------------------
# EDITAR MOTORISTA
# ----------------------------------------------------------------------
def editar_motorista(request, pk):
    motorista = get_object_or_404(Motorista, pk=pk)
    
    # Buscar todos os contratos ativos para o combobox
    contratos = Contrato.objects.filter(ativo=True).order_by('nome')

    if request.method == "POST":
        # O campo agora é "contrato" (select) ao invés de "id_contrato"
        contrato_id = request.POST.get("contrato")
        contrato_obj = Contrato.objects.filter(id=contrato_id).first() if contrato_id else None
        
        # O campo ativo agora vem como "True"/"False" string
        ativo = request.POST.get("ativo") == "True"

        motorista.nome = request.POST["nome"]
        motorista.cpf = request.POST["cpf"]
        motorista.telefone = request.POST["telefone"]
        motorista.cnh_numero = request.POST["cnh_numero"]
        motorista.cnh_categoria = request.POST["cnh_categoria"]
        motorista.cnh_vencimento = request.POST["cnh_vencimento"]
        motorista.ativo = ativo
        motorista.contrato = contrato_obj

        motorista.save()
        return redirect("lista_motoristas")

    return render(request, "motoristas/form.html", {
        "motorista": motorista,
        "contratos": contratos
    })


# ----------------------------------------------------------------------
# EXCLUIR / DESATIVAR
# ----------------------------------------------------------------------
def excluir_motorista(request, pk):
    motorista = get_object_or_404(Motorista, pk=pk)
    motorista.ativo = False
    motorista.save()
    return redirect("lista_motoristas")


# ----------------------------------------------------------------------
# DETALHES
# ----------------------------------------------------------------------
def detalhes_motorista(request, pk):
    motorista = get_object_or_404(Motorista, pk=pk)
    
    # Calcular dias para vencimento na view
    dias_para_vencimento = None
    if motorista.cnh_vencimento:
        hoje = date.today()
        diferenca = motorista.cnh_vencimento - hoje
        dias_para_vencimento = diferenca.days
    
    context = {
        'motorista': motorista,
        'dias_para_vencimento': dias_para_vencimento,  # Calculado na view
    }
    
    return render(request, "motoristas/partials/detalhes.html", context)





# ----------------------------------------------------------------------
# ATIVAR / DESATIVAR
# ----------------------------------------------------------------------
def toggle_motorista(request, pk):
    motorista = get_object_or_404(Motorista, pk=pk)
    motorista.ativo = not motorista.ativo
    motorista.save()
    return redirect("lista_motoristas")


# ----------------------------------------------------------------------
# EXPORTAR MOTORISTAS
# ----------------------------------------------------------------------
def exportar_motoristas(request):
    status = request.GET.get("status")

    if status == "ativo":
        motoristas = Motorista.objects.filter(ativo=True)
    elif status == "inativo":
        motoristas = Motorista.objects.filter(ativo=False)
    elif status == "vencimento":
        limite = dt_date.today() + timedelta(days=60)  # Usando dt_date
        motoristas = Motorista.objects.filter(cnh_vencimento__lte=limite)
    else:
        motoristas = Motorista.objects.all()

    # EXCEL
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Motoristas"

    headers = ["Nome", "CPF", "Telefone", "CNH Número", "Categoria", "Vencimento", "Status"]
    ws.append(headers)

    header_fill = PatternFill(start_color="00594C", end_color="00594C", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)
    center = Alignment(horizontal="center")
    left = Alignment(horizontal="left")
    thin_border = Border(
        left=Side(style="thin"), right=Side(style="thin"),
        top=Side(style="thin"), bottom=Side(style="thin")
    )

    # Estilo
    for col in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = center
        cell.border = thin_border

    # Linhas
    for m in motoristas:
        ws.append([
            m.nome,
            m.cpf,
            m.telefone,
            m.cnh_numero,
            m.cnh_categoria,
            m.cnh_vencimento.strftime("%d/%m/%Y") if m.cnh_vencimento else "",
            "Ativo" if m.ativo else "Inativo",
        ])

    # Zebra
    zebra_fill = PatternFill(start_color="F3F3F3", end_color="F3F3F3", fill_type="solid")
    for idx, row in enumerate(ws.iter_rows(min_row=2, max_row=ws.max_row), start=1):
        if idx % 2 == 0:
            for cell in row:
                cell.fill = zebra_fill
                cell.border = thin_border

    for column_cells in ws.columns:
        length = max(len(str(cell.value)) for cell in column_cells)
        ws.column_dimensions[column_cells[0].column_letter].width = length + 2

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:G{ws.max_row}"

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = "attachment; filename=motoristas.xlsx"
    wb.save(response)

    return response


# ----------------------------------------------------------------------
# AJAX PARA FILTROS
# ----------------------------------------------------------------------
def buscar_motoristas_ajax(request):
    status = request.GET.get("status") or "ativo"
    busca = request.GET.get("search")
    perfil = request.user.perfilusuario

    motoristas = Motorista.objects.all()

    # 🔥 Filtro por contrato do usuário
    if perfil.nivel != "adm" and perfil.contrato_id:
        motoristas = motoristas.filter(contrato_id=perfil.contrato_id)

    # Filtros de status
    if status == "ativo":
        motoristas = motoristas.filter(ativo=True)
    elif status == "inativo":
        motoristas = motoristas.filter(ativo=False)
    elif status == "vencimento":
        limite = dt_date.today() + timedelta(days=60)  # Usando dt_date
        motoristas = motoristas.filter(cnh_vencimento__lte=limite, ativo=True)

    # Busca
    if busca:
        motoristas = motoristas.filter(
            Q(nome__icontains=busca) |
            Q(cpf__icontains=busca) |
            Q(telefone__icontains=busca) |
            Q(cnh_numero__icontains=busca) |
            Q(cnh_categoria__icontains=busca)
        )

    return render(request, "motoristas/partials/cards.html", {
        "motoristas": motoristas,
        "status": status
    })