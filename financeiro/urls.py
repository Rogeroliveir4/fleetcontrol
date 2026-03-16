from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard_financeiro, name="dashboard_financeiro"),
    path("ipva/", views.lista_ipva, name="lista_ipva"),
]