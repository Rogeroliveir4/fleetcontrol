from django.urls import path
from . import views


urlpatterns = [
    # LISTAGEM & DETALHE
    path("", views.lista_movimentacoes, name="lista_movimentacoes"),
    path("filtrar/", views.filtrar_movimentacoes, name="filtrar_movimentacoes"),
    path("nova/", views.criar_movimentacao, name="criar_movimentacao"),
    path("<int:pk>/", views.movimentacao_detalhe, name="movimentacao_detalhe"),
    path("<int:pk>/retorno/", views.registrar_retorno, name="registrar_retorno"),
    path("exportar/", views.exportar_movimentacoes_excel, name="exportar_movimentacoes"),

    # ROTAS DE TERCEIROS
    path("terceiros/entrada/", views.terceiro_entrada, name="terceiro_entrada"),
    path("terceiros/portaria/", views.terceiros_portaria_lista, name="terceiros_portaria_lista"),
    path("terceiros/saida/<int:pk>/", views.terceiro_saida, name="terceiro_saida"),

    path("terceiros/exportar/", views.exportar_terceiros_excel, name="exportar_terceiros_excel"),
    path("terceiros/historico/", views.terceiros_historico, name="terceiros_historico"),
    path("terceiros/detalhe/<int:pk>/", views.terceiros_detalhe, name="terceiros_detalhe"),


    # ===============================
    # ✔ CHECKLIST MOTORISTA (CORRIGIDO)
    # ===============================
    path("solicitacao/<int:solicitacao_id>/checklist-saida/",views.checklist_saida_motorista, name="checklist_saida_motorista", ),

    path("portaria/saida/<int:movimentacao_id>/", views.portaria_registrar_saida, name="portaria_registrar_saida"),

    # ===============================
    # ✔ PORTARIA — RETORNO
    # ===============================
    path("portaria/retorno/", views.portaria_retorno_list,name="portaria_retorno_list",),

    
]


