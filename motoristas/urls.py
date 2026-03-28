from django.urls import path
from .views import (
    lista_motoristas,
    criar_motorista,
    editar_motorista,
    excluir_motorista,
    detalhes_motorista,
    toggle_motorista,
    exportar_motoristas,
    buscar_motoristas_ajax,
    baixar_modelo_motoristas,  
    importar_motoristas,       
)

urlpatterns = [
    path("", lista_motoristas, name="lista_motoristas"),
    path("adicionar/", criar_motorista, name="criar_motorista"),
    path("<int:pk>/editar/", editar_motorista, name="editar_motorista"),
    path("<int:pk>/excluir/", excluir_motorista, name="excluir_motorista"),
    
    # NOVAS ROTAS:
    path("<int:pk>/detalhes/", detalhes_motorista, name="detalhes_motorista"),
    path("<int:pk>/toggle/", toggle_motorista, name="toggle_motorista"),
    path("exportar/", exportar_motoristas, name="exportar_motoristas"),
    path("ajax/buscar/", buscar_motoristas_ajax, name="buscar_motoristas_ajax"),

    # Importação (CORRIGIDO - usando as funções já importadas)
    path('importar/', importar_motoristas, name='importar_motoristas'),
    path('modelo/', baixar_modelo_motoristas, name='baixar_modelo_motoristas'),
]