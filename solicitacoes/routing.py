from django.urls import re_path
from .consumers import GestorSolicitacaoConsumer, PortariaConsumer

websocket_urlpatterns = [
    re_path(r"ws/gestor/solicitacoes/$", GestorSolicitacaoConsumer.as_asgi()),
    re_path(r"ws/portaria/$", PortariaConsumer.as_asgi()),
]
