from django.urls import path
from . import views

urlpatterns = [
    path("dashboard/", views.dashboard_solicitante, name="dashboard_solicitante"),
    path("solicitar/<int:veiculo_id>/", views.solicitar_veiculo, name="solicitante_solicitar"),
]
