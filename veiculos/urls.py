from django.urls import path
from . import views

urlpatterns = [
    # Lista principal
    path('', views.lista_veiculos, name='lista_veiculos'),
    
    
    # CRUD
    path('novo/', views.criar_veiculo, name='criar_veiculo'),
    path('<int:id>/', views.detalhes_veiculo, name='detalhes_veiculo'),
    path('<int:id>/editar/', views.editar_veiculo, name='editar_veiculo'),
    path('<int:id>/excluir/', views.excluir_veiculo, name='excluir_veiculo'),
    
    # Ações
    path('<int:id>/atualizar-km/', views.atualizar_km, name='atualizar_km'),
    path('<int:id>/alterar-status/', views.alterar_status, name='alterar_status'),
    
    # Exportação
    path('exportar/', views.exportar_excel, name='exportar_excel'),

    # validação AJAX
    path('api/check-placa/', views.check_placa, name='check_placa'),
    path('api/check-tag-interna/', views.check_tag_interna, name='check_tag_interna'),
]
