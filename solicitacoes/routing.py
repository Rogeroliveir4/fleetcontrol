from django.urls import re_path
from .consumers import GestorSolicitacaoConsumer

websocket_urlpatterns = [
    re_path(r"ws/gestor/solicitacoes/$", GestorSolicitacaoConsumer.as_asgi()),
]
