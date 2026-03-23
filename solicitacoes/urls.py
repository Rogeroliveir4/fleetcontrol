from django.urls import path
from . import views
from movimentacoes import views as movimentacoes_views

urlpatterns = [
    # Motorista / ADM — criar solicitação
    path("solicitar/<int:veiculo_id>/", views.solicitar_veiculo, name="solicitar_veiculo"),
    
    # DETALHES DA SOLICITAÇÃO (NOVA ROTA - ADICIONE ESTA LINHA) ✓
    path("detalhes/<int:solicitacao_id>/", views.detalhes_solicitacao, name="detalhes_solicitacao"),
    
    # Gestor — lista de solicitações
    path('gestor/', views.gestor_solicitacoes, name='gestor_solicitacoes'),
    
    # Gestor — ações
    path('gestor/aprovar/<int:id>/', views.aprovar_solicitacao, name='aprovar_solicitacao'),
    path('gestor/reprovar/<int:id>/', views.reprovar_solicitacao, name='reprovar_solicitacao'),
    path("portaria/saidas/", views.listar_saidas_portaria, name="listar_saidas_portaria"),

    path("portaria/saida/<int:solicitacao_id>/", movimentacoes_views.portaria_registrar_saida, name="portaria_registrar_saida"),

    # PORTARIA — exportar saídas
    path('portaria/saidas/exportar/', views.exportar_saidas_portaria_excel, name='exportar_saidas_portaria_excel'),
    # GESTOR / GERAL — exportar solicitações
    path('exportar/', views.exportar_excel_solicitacoes, name='exportar_excel_solicitacoes'),
    
    path("visualizar/<int:pk>/", views.visualizar_solicitacao, name="visualizar_solicitacao"),
    path("<int:pk>/", views.solicitacao_detalhe, name="solicitacao_detalhe"),

    # Cancelar solicitação (USUÁRIO) 
    path("cancelar/<int:pk>/", views.cancelar_solicitacao,  name="cancelar_solicitacao"),

    # Editar solicitação (USUÁRIO)
    path("editar/<int:pk>/", views.editar_solicitacao,  name="editar_solicitacao"),



]