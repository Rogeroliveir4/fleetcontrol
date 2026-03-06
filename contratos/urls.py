from django.urls import path
from . import views

urlpatterns = [
    # ... outras URLs
    path('contratos/buscar/', views.buscar_contratos, name='buscar_contratos'),
]