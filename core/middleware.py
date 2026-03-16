from django.shortcuts import redirect
from django.urls import reverse


class LoginRequiredMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

        # Rotas públicas exatas
        self.public_urls = [
            reverse("login"),
            reverse("password_reset"),
            reverse("password_reset_done"),
            reverse("password_reset_complete"),
        ]

        # Rotas públicas com parâmetros dinâmicos
        self.public_prefixes = [
            "/password-reset-confirm/",
        ]

    def __call__(self, request):

        path = request.path

        # Ignorar arquivos estáticos e media
        if path.startswith("/static/") or path.startswith("/media/"):
            return self.get_response(request)

        # Verificar rotas com prefixo (reset confirm)
        for prefix in self.public_prefixes:
            if path.startswith(prefix):
                return self.get_response(request)

        # Verificar rotas públicas exatas
        if path in self.public_urls:
            return self.get_response(request)

        # Se não estiver autenticado
        if not request.user.is_authenticated:
            return redirect("login")

        return self.get_response(request)