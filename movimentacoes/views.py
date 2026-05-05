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
from .models import MovimentacaoTerceiro
from contratos.models import Contrato
from django.utils.timezone import localtime
from PIL import Image
from django.core.files.uploadedfile import UploadedFile
import io
import uuid
from django.db import transaction


# FUNÇÃO AUXILIAR PARA APLICAR FILTROS (REUTILIZÁVEL)
@login_required
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
        queryset = queryset.filter(
            data_retorno__isnull=True
        ).exclude(
            status="encerrado_sem_retorno"
        )
    elif status == "finalizada":
        queryset = queryset.filter(
            Q(data_retorno__isnull=False) | 
            Q(status="encerrado_sem_retorno")
        )

    #  DATA
    if inicio:
        queryset = queryset.filter(data_saida__date__gte=inicio)

    if fim:
        queryset = queryset.filter(data_saida__date__lte=fim)

    return queryset





# LISTA DE MOVIMENTAÇÕES COM FILTROS E PAGINAÇÃO
@login_required
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

    # Query base otimizada com select_related para evitar N+1
    movs = (
        Movimentacao.objects
        .select_related("veiculo", "motorista", "solicitacao", "solicitacao__contrato")
        .order_by("-data_saida")
    )

    # FILTRO INICIAL PARA EXIBIR APENAS MOVIMENTAÇÕES COM DATA DE SAÍDA (EVITAR RASCUNHOS)
    movs = movs.filter(data_saida__isnull=False)

    # FILTRO AUTOMÁTICO POR CONTRATO (GESTOR)
    perfil = getattr(request.user, "perfilusuario", None)

    if perfil and perfil.nivel == "gestor" and perfil.contrato:
        movs = movs.filter(
            Q(contrato=perfil.contrato) |
            Q(contrato__isnull=True, solicitacao__contrato=perfil.contrato)
        )

    # APLICAR FILTROS DE BUSCA
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
    
    # FILTRO DE STATUS (CORRIGIDO)
    if status == "transito":
        # Em trânsito: sem data_retorno E não encerrado
        movs = movs.filter(
            data_retorno__isnull=True
        ).exclude(
            status="encerrado_sem_retorno"
        )
    elif status == "finalizada":
        # Finalizadas: com data_retorno OU encerradas sem retorno
        movs = movs.filter(
            Q(data_retorno__isnull=False) | 
            Q(status="encerrado_sem_retorno")
        )
    # Se status for vazio ou outro valor, mostra todas

    # FILTROS DE DATA
    if inicio:
        movs = movs.filter(data_saida__date__gte=inicio)
    if fim:
        movs = movs.filter(data_saida__date__lte=fim)

    # Paginação
    paginator = Paginator(movs, limite)
    page = request.GET.get("page")
    movimentacoes = paginator.get_page(page)

    # ============================================
    # CONTADORES CORRIGIDOS
    # ============================================
    # Base com restrição de contrato (se aplicável)
    base_count = Movimentacao.objects.filter(data_saida__isnull=False)
    
    if perfil and perfil.nivel == "gestor" and perfil.contrato:
        base_count = base_count.filter(
            Q(contrato=perfil.contrato) |
            Q(contrato__isnull=True, solicitacao__contrato=perfil.contrato)
        )

    #   Trânsito = sem retorno E não encerrado
    total_transito = base_count.filter(
        data_retorno__isnull=True
    ).exclude(
        status="encerrado_sem_retorno"
    ).count()
    
    # Finalizadas = com retorno OU encerradas
    total_finalizada = base_count.filter(
        Q(data_retorno__isnull=False) | 
        Q(status="encerrado_sem_retorno")
    ).count()
    
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


# ENCERRAR MOVIMENTAÇÃO SEM RETORNO (GESTOR/ADMIN)
@login_required
def encerrar_movimentacao(request, pk):
    """Encerra uma movimentação sem retorno - apenas para gestores/admin"""
    
    mov = get_object_or_404(Movimentacao, pk=pk)

    # Permissão
    perfil = getattr(request.user, "perfilusuario", None)
    if not perfil or perfil.nivel not in ["gestor", "adm"]:
        messages.error(request, "Você não tem permissão para encerrar movimentações.")
        return redirect("lista_movimentacoes")

    # Status permitidos
    status_permitidos = [
        "em_andamento", 
        "aguardando_checklist_retorno", 
        "aguardando_retorno_portaria",
        "divergencia_km"
    ]

    if mov.status not in status_permitidos:
        messages.error(request, f"Movimentação com status '{mov.get_status_display()}' não pode ser encerrada.")
        return redirect("lista_movimentacoes")

    if request.method == "POST":
        motivo = request.POST.get("motivo", "").strip()

        if not motivo:
            messages.error(request, "O motivo do encerramento é obrigatório.")
            return redirect("lista_movimentacoes")

        try:
            # =========================================
            # BLOCO CRÍTICO (ATOMIC)
            # =========================================
            with transaction.atomic():

                mov.status = "encerrado_sem_retorno"
                mov.encerrado_por = request.user
                mov.encerrado_em = timezone.now()
                mov.motivo_encerramento = motivo
                mov.save()

                if mov.solicitacao:
                    mov.solicitacao.status = "FINALIZADA"
                    mov.solicitacao.save()

            # =========================================
            # FORA DO ATOMIC (VEÍCULO)
            # =========================================
            veiculo = mov.veiculo

            status_inativo = "Inativo"
            status_validos = [s[0] for s in Veiculo.STATUS_CHOICES]

            if status_inativo not in status_validos:
                status_inativo = "Manutencao" if "Manutencao" in status_validos else "Disponivel"

            try:
                veiculo.status = status_inativo
                veiculo.ativo = False
                veiculo.save(update_fields=["status", "ativo"], skip_clean=True)
            except Exception as e:
                print("ERRO VEICULO >>>", str(e))

            # =========================================
            # SUCESSO
            # =========================================
            messages.success(request, "Movimentação encerrada com sucesso!")
            return redirect("lista_movimentacoes")

        except Exception as e:
            import traceback
            print("ERRO ENCERRAR >>>", traceback.format_exc())

            messages.error(request, "Erro ao encerrar movimentação.")
            return redirect("lista_movimentacoes")

    # GET
    context = {
        "mov": mov,
        "acao": "encerrar",
    }

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        html = render_to_string(
            "movimentacoes/modals/encerrar.html",
            context,
            request=request
        )
        return JsonResponse({"html": html})

    return render(request, "movimentacoes/modals/encerrar.html", context)


# EDITAR MOVIMENTAÇÃO (GESTOR/ADMIN)
@login_required
def editar_movimentacao(request, pk):
    mov = get_object_or_404(Movimentacao, pk=pk)

    perfil = getattr(request.user, "perfilusuario", None)
    if not perfil or perfil.nivel not in ["gestor", "adm"]:
        messages.error(request, "Você não tem permissão para editar movimentações.")
        return redirect("lista_movimentacoes")

    if request.method == "POST":

        try:
            with transaction.atomic():

                # =========================================
                # CAPTURA VALORES ANTIGOS (AUDITORIA)
                # =========================================
                km_saida_antigo = mov.km_saida
                km_retorno_antigo = mov.km_retorno

                # =========================================
                # CAMPOS
                # =========================================
                destino = request.POST.get("destino", "").strip().upper()
                observacao = request.POST.get("observacao", "").strip()

                km_saida_str = request.POST.get("km_saida", "").strip()
                km_retorno_str = request.POST.get("km_retorno", "").strip()
                motivo_ajuste = request.POST.get("motivo_edicao", "").strip()

                erros = []

                # =========================================
                # PARSE INTELIGENTE
                # =========================================
                def parse_km(valor, atual):
                    if not valor:
                        return atual, False
                    try:
                        return int(valor.replace(".", "").replace(",", "")), True
                    except:
                        return None, True

                km_saida_novo, alterou_saida = parse_km(km_saida_str, mov.km_saida)
                km_retorno_novo, alterou_retorno = parse_km(km_retorno_str, mov.km_retorno)

                # =========================================
                # VALIDAÇÕES
                # =========================================
                if alterou_saida and km_saida_novo is None:
                    erros.append("KM de saída inválido.")

                if alterou_retorno and km_retorno_novo is None:
                    erros.append("KM de retorno inválido.")

                if not alterou_saida and not alterou_retorno:
                    erros.append("Nenhuma alteração foi realizada.")

                if km_saida_novo and km_retorno_novo:
                    if km_saida_novo > km_retorno_novo:
                        erros.append("KM de saída não pode ser maior que KM de retorno.")

                if (alterou_saida or alterou_retorno):
                    if not motivo_ajuste or len(motivo_ajuste) < 10:
                        erros.append("Informe um motivo válido (mínimo 10 caracteres).")

                if erros:
                    for erro in erros:
                        messages.error(request, erro)
                    return render(request, "movimentacoes/editar.html", {
                        "mov": mov,
                        "motivo_edicao": motivo_ajuste,
                    })

                # =========================================
                # AUDITORIA (LOG COMPLETO)
                # =========================================
                from .models import HistoricoEdicao

                HistoricoEdicao.objects.create(
                    movimentacao=mov,
                    editado_por=request.user,
                    motivo_edicao=motivo_ajuste,
                    km_saida_anterior=km_saida_antigo,
                    km_saida_novo=km_saida_novo,
                    km_retorno_anterior=km_retorno_antigo,
                    km_retorno_novo=km_retorno_novo,
                )

                # SALVAR ANTERIORES (PARA TEMPLATE)
                if km_saida_antigo != km_saida_novo:
                    mov.km_saida_anterior = km_saida_antigo

                if km_retorno_antigo != km_retorno_novo:
                    mov.km_retorno_anterior = km_retorno_antigo

                # ATUALIZAÇÃO
                mov.destino = destino
                mov.observacao = observacao
                mov.km_saida = km_saida_novo
                mov.km_retorno = km_retorno_novo

                if km_saida_novo and km_retorno_novo:
                    mov.distancia_percorrida = km_retorno_novo - km_saida_novo

                mov.editado_por = request.user
                mov.editado_em = timezone.now()
                mov.motivo_edicao = motivo_ajuste

                mov.save()

                # ATUALIZAÇÃO DO VEÍCULO
                veiculo = mov.veiculo

                if mov.data_saida:
                    existe_mov_mais_recente = Movimentacao.objects.filter(
                        veiculo=veiculo,
                        data_saida__gt=mov.data_saida
                    ).exists()

                    if not existe_mov_mais_recente:

                        # ATUALIZA KM (SEM INTERFERIR NO STATUS)
                        km_base = None

                        # só usa retorno se existir
                        if mov.km_retorno:
                            km_base = mov.km_retorno

                        # só usa saída se NÃO existe retorno
                        elif mov.km_saida and not mov.km_retorno:
                            km_base = mov.km_saida

                        if km_base:
                            veiculo.km_atual = km_base

                        veiculo.save(update_fields=["km_atual", "status"])

                # FEEDBACK
                messages.success(
                    request,
                    f"Ajuste realizado com sucesso! "
                    f"Saída: {km_saida_antigo} → {mov.km_saida} | "
                    f"Retorno: {km_retorno_antigo} → {mov.km_retorno}"
                )

                return redirect("lista_movimentacoes")

        except Exception as e:
            messages.error(request, f"Erro ao editar movimentação: {str(e)}")
            return render(request, "movimentacoes/editar.html", {"mov": mov})

    return render(request, "movimentacoes/editar.html", {
        "mov": mov,
        "acao": "editar",
        "status_choices": Movimentacao.STATUS_CHOICES,
    })



# API PARA ENCERRAR (ALTERNATIVA VIA AJAX)
@login_required
def api_encerrar_movimentacao(request, pk):
    """Endpoint AJAX para encerrar movimentação"""
    if request.method != "POST":
        return JsonResponse({"error": "Método não permitido"}, status=405)
    
    mov = get_object_or_404(Movimentacao, pk=pk)
    
    # Verificar permissão
    perfil = getattr(request.user, "perfilusuario", None)
    if not perfil or perfil.nivel not in ["gestor", "adm"]:
        return JsonResponse({"error": "Permissão negada"}, status=403)
    
    motivo = request.POST.get("motivo", "").strip()
    if not motivo:
        return JsonResponse({"error": "Motivo é obrigatório"}, status=400)
    
    try:
        with transaction.atomic():
            # Atualizar movimentação
            mov.status = "encerrado_sem_retorno"
            mov.encerrado_por = request.user
            mov.encerrado_em = timezone.now()
            mov.motivo_encerramento = motivo
            mov.save()
            
            # Atualizar solicitação vinculada
            if mov.solicitacao:
                mov.solicitacao.status = "FINALIZADA"
                mov.solicitacao.save()
            
            #  CORRIGIDO: Mudar status do veículo para "Inativo"
            veiculo = mov.veiculo
            
            # Verificar status disponíveis no modelo Veiculo
            status_validos = [s[0] for s in Veiculo.STATUS_CHOICES]
            
            if "Inativo" in status_validos:
                veiculo.status = "Inativo"
            elif "Baixado" in status_validos:
                veiculo.status = "Baixado"
            elif "Manutencao" in status_validos:
                veiculo.status = "Manutencao"
            else:
                # Último fallback: manter como está mas logar erro
                print(f"ALERTA: Nenhum status de inatividade encontrado para veículo {veiculo.id}")
                veiculo.ativo = False  # Marcar como inativo
            
            veiculo.save()
            
        return JsonResponse({
            "success": True,
            "message": "Movimentação encerrada com sucesso",
            "novo_status": mov.get_status_display()
        })
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)



@login_required
def filtrar_movimentacoes(request):
    # Verificar se é requisição AJAX
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    # Parâmetros
    status = request.GET.get("status", "")
    search = request.GET.get("search", "").strip()
    inicio = request.GET.get("inicio", "")
    fim = request.GET.get("fim", "")
    page = request.GET.get("page", 1)

    # Limite por página
    try:
        limite = int(request.GET.get("limite", 12))
        if limite not in [5, 10, 15, 20, 30]:
            limite = 12
    except:
        limite = 12

    # Query base (mantida, só otimizada)
    movs = Movimentacao.objects.select_related(
        "veiculo", 
        "motorista", 
        "solicitacao", 
        "solicitacao__contrato"
    ).order_by("-data_saida")

    # =========================================
    # FILTRO POR CONTRATO
    # =========================================
    perfil = getattr(request.user, "perfilusuario", None)
    
    if perfil and perfil.nivel == "gestor" and perfil.contrato:
        movs = movs.filter(
            Q(contrato=perfil.contrato) |
            Q(contrato__isnull=True, solicitacao__contrato=perfil.contrato)
        )

    # =========================================
    # BUSCA
    # =========================================
    if search:
        search = search.strip()

        # TAG (ex: VA-100)
        if "-" in search and search.upper().startswith("VA"):
            movs = movs.filter(veiculo__tag_interna__iexact=search)

        # PLACA (ABC-1234)
        elif "-" in search and len(search) >= 7:
            movs = movs.filter(veiculo__placa__iexact=search)

        # ID
        elif search.isdigit():
            movs = movs.filter(id=int(search))

        # Busca geral
        else:
            movs = movs.filter(
                Q(veiculo__placa__icontains=search) |
                Q(motorista__nome__icontains=search) |
                Q(veiculo__modelo__icontains=search) |
                Q(veiculo__marca__icontains=search) |
                Q(veiculo__tag_interna__icontains=search)
            )

    # =========================================
    # FILTRO DE STATUS (AJUSTADO — SEM QUEBRAR)
    # =========================================
    if status == "transito":
        movs = movs.filter(
            status__in=[
                "em_andamento",
                "aguardando_checklist_retorno",
                "aguardando_retorno_portaria",
                "divergencia_km"
            ]
        )

    elif status == "finalizada":
        movs = movs.filter(
            status__in=[
                "finalizado",
                "encerrado_sem_retorno"
            ]
        )

    # =========================================
    # FILTRO POR DATA
    # =========================================
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

    # =========================================
    # PAGINAÇÃO
    # =========================================
    paginator = Paginator(movs, limite)
    
    try:
        movimentacoes = paginator.get_page(page)
    except:
        movimentacoes = paginator.get_page(1)

    # Contexto
    context = {
        "movimentacoes": movimentacoes,
        "status": status,
        "search": search,
        "inicio": inicio,
        "fim": fim,
        "page_obj": movimentacoes,
        "request": request,
    }

    
    # RESPOSTA AJAX
    if is_ajax:
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
        status="Disponivel", ativo=True
    ).exclude(
        id__in=veiculos_em_uso
    )

    if perfil and perfil.nivel != "adm":
        veiculos = veiculos.filter(contrato=perfil.contrato)


    # MOTORISTAS DISPONÍVEIS
    motoristas = Motorista.objects.exclude(
        id__in=list(motoristas_mov_em_uso) + list(motoristas_sol_em_uso)
    )

    # Restrição por contrato (gestor)
    if perfil and perfil.nivel != "adm":
        motoristas = motoristas.filter(contrato=perfil.contrato)


    # SOLICITAÇÃO (SE VIER)
    solicitacao_id = request.GET.get("solicitacao_id") or request.POST.get("solicitacao_id")
    solicitacao = None

# Se for edição manual, não deve vir solicitacao_id. Se for criação a partir de solicitação, deve vir e preencher os campos automaticamente.
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



"""
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

"""




# FUNÇÃO AUXILIAR PARA COMPRESSÃO DE IMAGENS (PORTARIA)
def compress_image(image_file, quality=65, max_width=1280):
    if not image_file:
        return image_file

    try:
        img = Image.open(image_file)

        #  converter sempre
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')

        #  redimensionar sempre (não só grandes)
        if img.width > max_width:
            ratio = max_width / img.width
            new_size = (int(img.width * ratio), int(img.height * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)

        #  salvar comprimido SEMPRE
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=quality, optimize=True)

        output.seek(0)

        return UploadedFile(
            output,
            name=image_file.name.split('.')[0] + ".jpg",
            content_type='image/jpeg'
        )

    except Exception as e:
        print(f"Erro compressão: {e}")
        return image_file


# REGISTRA A SAÍDA - PORTARIA (SIMPLIFICADA)
@login_required
def portaria_registrar_saida(request, solicitacao_id):

    # LOCK OPTIMISTA PARA EVITAR CONCORRÊNCIA
    with transaction.atomic():

        solicitacao = (
            SolicitacaoVeiculo.objects
            .select_for_update()
            .get(id=solicitacao_id)
        )

        if solicitacao.status != "AGUARDANDO_SAIDA_PORTARIA":
            messages.error(request, "Essa solicitação não está disponível para saída.")
            return redirect("listar_saidas_portaria")

        mov_existente = Movimentacao.objects.filter(
            solicitacao=solicitacao,
            data_retorno__isnull=True
        ).exists()

        if mov_existente:
            messages.warning(request, "Essa saída já foi registrada.")
            return redirect("listar_saidas_portaria")

        if request.method == "POST":

            contrato = (
                solicitacao.contrato or
                getattr(solicitacao.veiculo, "contrato", None) or
                getattr(request.user.perfilusuario, "contrato", None)
            )

            # Criar movimentação
            mov = Movimentacao(
                solicitacao=solicitacao,
                veiculo=solicitacao.veiculo,
                motorista=solicitacao.motorista,
                destino=solicitacao.destino,
                contrato=contrato,
                km_saida=solicitacao.veiculo.km_atual,
                data_saida=timezone.now(),
                status="em_andamento",
                porteiro_saida=request.user,
                porteiro_saida_nome=request.user.get_full_name() or request.user.username,
                observacao=request.POST.get("observacao", "").strip(),
                observacao_portaria=request.POST.get("observacao_portaria", "").strip(),
                com_cacamba=request.POST.get("com_cacamba") in ["true", "on"],
                com_prancha=request.POST.get("com_prancha") in ["true", "on"],
            )

            # Campos novos (se existirem no modelo)
            if hasattr(mov, 'com_malas'):
                mov.com_malas = request.POST.get("com_malas") in ["true", "on"]
            if hasattr(mov, 'com_outros_itens'):
                mov.com_outros_itens = request.POST.get("com_outros_itens") in ["true", "on"]

            # Fotos da saída
            if request.FILES.get("foto_portaria_geral"):
                mov.foto_portaria_geral = compress_image(request.FILES["foto_portaria_geral"])

            if request.FILES.get("foto_portaria_avaria"):
                mov.foto_portaria_avaria = compress_image(request.FILES["foto_portaria_avaria"])

            if request.FILES.get("foto_portaria_painel"):
                mov.foto_portaria_painel = compress_image(request.FILES["foto_portaria_painel"])

            if request.FILES.get("foto_portaria_equipamento"):
                mov.foto_portaria_equipamento = compress_image(request.FILES["foto_portaria_equipamento"])

            # Foto do interior/porta-malas (se o campo existir no modelo)
            if request.FILES.get("foto_portaria_interior"):
                if hasattr(mov, 'foto_portaria_interior'):
                    mov.foto_portaria_interior = compress_image(request.FILES["foto_portaria_interior"])

            mov.save()

            # Atualiza solicitação
            solicitacao.status = "EM_TRANSITO"
            solicitacao.data_saida = mov.data_saida
            solicitacao.save(update_fields=["status", "data_saida"])

            # Atualiza status do veículo
            veiculo = solicitacao.veiculo
            veiculo.status = "EmTransito"
            veiculo.save(update_fields=["status"])

            messages.success(request, "Saída registrada com sucesso.")
            return redirect("/movimentacoes/?status=transito")

    return render(request, "movimentacoes/portaria/saida_registro.html", {
        "solicitacao": solicitacao,
    })


    
# REGISTRAR RETORNO (PORTARIA)
@login_required
def registrar_retorno(request, pk):
    mov = get_object_or_404(Movimentacao, pk=pk)
    
    # DEFINIR CONTEXTO (PORTARIA x MANUAL)
    perfil = getattr(request.user, "perfilusuario", None)
    
    # Template por perfil
    if perfil and perfil.nivel == "portaria"  or perfil.nivel == "gestor" :
        template = "movimentacoes/retorno_portaria.html"
    else:
        template = "movimentacoes/retorno.html"

    status_permitidos = [
    "em_andamento",
    "aguardando_retorno_portaria",
    "aguardando_checklist_retorno"
    ]

    if mov.status not in status_permitidos:
        messages.error(
            request,
            f"Não é possível registrar retorno para uma movimentação com status '{mov.get_status_display()}'."
        )
        return redirect("lista_movimentacoes")    
    
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
        

        # PORTEIRO + FOTOS (RETORNO) COM COMPRESSÃO
        if perfil and perfil.nivel == "portaria":
            mov.porteiro_retorno = request.user
            mov.porteiro_retorno_nome = (
                request.user.get_full_name() or request.user.username
            )
            
            # Aplicar compressão em todas as fotos
            foto_geral = request.FILES.get("foto_retorno_geral")
            if foto_geral:
                mov.foto_retorno_geral = compress_image(foto_geral)
            
            foto_painel = request.FILES.get("foto_retorno_painel")
            if foto_painel:
                mov.foto_retorno_painel = compress_image(foto_painel)
            
            foto_avaria = request.FILES.get("foto_retorno_avaria")
            if foto_avaria:
                mov.foto_retorno_avaria = compress_image(foto_avaria)
            
            foto_equipamento = request.FILES.get("foto_retorno_equipamento")
            if foto_equipamento:
                mov.foto_retorno_equipamento = compress_image(foto_equipamento)
            
            foto_cacamba = request.FILES.get("foto_retorno_cacamba")
            if foto_cacamba:
                mov.foto_retorno_cacamba = compress_image(foto_cacamba)
            
            foto_prancha = request.FILES.get("foto_retorno_prancha")
            if foto_prancha:
                mov.foto_retorno_prancha = compress_image(foto_prancha)
            
            foto_porta_malas = request.FILES.get("foto_retorno_porta_malas")
            if foto_porta_malas:
                mov.foto_retorno_porta_malas = compress_image(foto_porta_malas)
            
            foto_combustivel = request.FILES.get("foto_retorno_combustivel")
            if foto_combustivel:
                mov.foto_retorno_combustivel = compress_image(foto_combustivel)
        
        mov.save()
        

        # SOLICITAÇÃO VINCULADA
        if mov.solicitacao:
            mov.solicitacao.status = "FINALIZADA"
            mov.solicitacao.data_retorno = mov.data_retorno
            mov.solicitacao.save()
        

        # VEÍCULO - ATUALIZAR SEM VALIDAÇÕES
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

""" RETORNO DO MOTORISTA
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


"""




MAX_UPLOAD_MB = 8

def validar_imagem(file):
    if file.size > MAX_UPLOAD_MB * 1024 * 1024:
        raise ValueError(f"Imagem muito grande ({file.size/1024/1024:.1f}MB). Máx: {MAX_UPLOAD_MB}MB")


def processar_imagem(file):
    if not file:
        return None

    validar_imagem(file)

    img = compress_image(file)

    #  nome único
    nome = f"{uuid.uuid4().hex}.jpg"
    img.name = nome

    return img


# REGISTRAR ENTRADA DE TERCEIRO (PORTARIA)
@login_required
def terceiro_entrada(request):
    if request.method == "POST":
        try:
            #  processa imagens
            foto_veiculo = processar_imagem(request.FILES.get("foto_veiculo"))
            foto_motorista = processar_imagem(request.FILES.get("foto_motorista"))
            foto_material = processar_imagem(request.FILES.get("foto_material"))

            #  valida obrigatória
            if not foto_veiculo:
                raise ValueError("A foto do veículo é obrigatória")

            #  cria registro COMPLETO
            MovimentacaoTerceiro.objects.create(
                placa=request.POST.get("placa", "").upper(),
                tipo_veiculo=request.POST.get("tipo_veiculo"),
                empresa=request.POST.get("empresa", "").upper(),
                motorista_nome=request.POST.get("motorista_nome", "").upper(),
                #documento=request.POST.get("documento"),

                descricao_veiculo=request.POST.get("descricao_veiculo", ""),
                tags=request.POST.get("tags", "").upper(),

                motivo_entrada=request.POST.get("motivo", ""),
                observacoes_entrada=request.POST.get("observacoes", ""),
                descricao_material=request.POST.get("descricao_material", ""),

                status="ENTRADA",

                porteiro_entrada=request.user,
                porteiro_entrada_nome=request.user.get_full_name() or request.user.username,

                #  imagens
                foto_veiculo=foto_veiculo,
                foto_motorista=foto_motorista,
                foto_material=foto_material,
            )

            messages.success(request, "Entrada registrada com sucesso.")
            return redirect("terceiros_portaria_lista")

        except ValueError as e:
            messages.error(request, str(e))
            return redirect(request.path)

        except Exception as e:
            print("Erro ao salvar entrada:", e)
            messages.error(request, "Erro ao registrar entrada.")
            return redirect(request.path)

    return render(request, "movimentacoes/terceiros/entrada.html")

# CONTADOR DE SOLICITAÇÕES PENDENTES PARA PORTARIA

@login_required
def contador_portaria(request):
    perfil = request.user.perfilusuario

    if perfil.nivel != "portaria":
        return JsonResponse({"erro": "não autorizado"}, status=403)

    qtd = SolicitacaoVeiculo.objects.filter(
        contrato=perfil.contrato,
        status="AGUARDANDO_SAIDA_PORTARIA"
    ).count()

    return JsonResponse({"pendentes": qtd})

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


MAX_UPLOAD_MB = 8

def validar_imagem(file):
    if file and file.size > MAX_UPLOAD_MB * 1024 * 1024:
        raise ValueError(f"Imagem muito grande ({file.size/1024/1024:.1f}MB). Máx: {MAX_UPLOAD_MB}MB")


def processar_imagem(file):
    if not file:
        return None

    validar_imagem(file)

    img = compress_image(file)

    #  nome único
    img.name = f"{uuid.uuid4().hex}.jpg"

    return img



# REGISTRAR SAÍDA DE TERCEIRO (PORTARIA)
@login_required
def terceiro_saida(request, pk):
    perfil = getattr(request.user, "perfilusuario", None)

    if not perfil or perfil.nivel not in ["portaria", "gestor", "adm"]:
        messages.error(request, "Acesso não autorizado.")
        return redirect("dashboard")

    mov = get_object_or_404(
        MovimentacaoTerceiro,
        pk=pk,
        status="ENTRADA"
    )

    if request.method == "POST":
        try:
            #  processa imagens
            foto_saida_veiculo = processar_imagem(request.FILES.get("foto_saida_veiculo"))
            foto_saida_avaria = processar_imagem(request.FILES.get("foto_saida_avaria"))
            foto_saida_extra = processar_imagem(request.FILES.get("foto_saida_extra"))

            #  dados principais
            mov.data_saida = timezone.now()
            mov.porteiro_saida = request.user
            mov.porteiro_saida_nome = request.user.get_full_name() or request.user.username
            mov.observacoes_saida = request.POST.get("observacoes", "")

            #  aplica imagens
            if foto_saida_veiculo:
                mov.foto_saida_veiculo = foto_saida_veiculo
            if foto_saida_avaria:
                mov.foto_saida_avaria = foto_saida_avaria
            if foto_saida_extra:
                mov.foto_saida_extra = foto_saida_extra

            mov.status = "SAIDA"
            mov.save()

            messages.success(request, "Saída registrada com sucesso.")
            return redirect("terceiros_portaria_lista")

        except ValueError as e:
            messages.error(request, str(e))
            return redirect(request.path)

        except Exception as e:
            print("Erro saída terceiros:", e)
            messages.error(request, "Erro ao registrar saída.")
            return redirect(request.path)

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