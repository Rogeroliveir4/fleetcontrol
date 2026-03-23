from django.contrib import admin
from django.urls import path, include
from . import views
from django.conf import settings
from django.conf.urls.static import static
from solicitacoes import views as solicitacoes_views
from django.urls import path, include


urlpatterns = [

    # Painel administrativo
    path("admin/", admin.site.urls),

    # Autenticação / Login / Logout
    path("", include("contas.urls")),

    # Dashboard
    path("dashboard/", views.dashboard, name="dashboard"),

    # Aplicações principais
    path("veiculos/", include("veiculos.urls")),
    path("motoristas/", include("motoristas.urls")),
    path("movimentacoes/", include("movimentacoes.urls")),
    path('solicitacoes/', include('solicitacoes.urls')),
    
    path("dashboard/motorista/", views.dashboard_motorista, name="dashboard_motorista"),

    path("dashboard/gestor/", views.dashboard_gestor, name="dashboard_gestor"),
    
        # ROTAS DO GESTOR (necessárias!)
        # path("gestor/solicitacoes/", views.gestor_solicitacoes, name="gestor_solicitacoes"),
        #  path("gestor/solicitacoes/aprovar/<int:id>/", views.aprovar_solicitacao, name="aprovar_solicitacao"),
        # path("gestor/solicitacoes/reprovar/<int:id>/", views.reprovar_solicitacao, name="reprovar_solicitacao"),"""
        
    path("contratos/", include("contratos.urls")),
    # path("__reload__/", include("django_browser_reload.urls")),
    path("solicitacoes/minhas/", solicitacoes_views.minhas_solicitacoes, name="minhas_solicitacoes"),

    #ROTAS DO FINANCEIRO DE IPVA
    path('financeiro/', include('financeiro.urls')),



    path("solicitante/", include("solicitantes.urls")),



]


urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)