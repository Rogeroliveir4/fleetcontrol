from django.shortcuts import redirect
from django.urls import reverse

class LoginRequiredMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

        self.public_urls = [
            reverse("login"),
            reverse("password_reset"),
            reverse("password_reset_done"),
        ]

        #  ROTAS DINÂMICAS
        self.public_prefixes = [
            "/reset/",
            "/password-reset-confirm/",   #  ADICIONA ISSO
        ]

    def __call__(self, request):

        path = request.path

        # Static / media
        if path.startswith("/static/") or path.startswith("/media/"):
            return self.get_response(request)

        # Admin
        if path.startswith("/admin/"):
            return self.get_response(request)

        #  LIBERA PREFIXOS DINÂMICOS
        if any(path.startswith(p) for p in self.public_prefixes):
            return self.get_response(request)

        # URLs públicas exatas
        if path in self.public_urls:
            return self.get_response(request)

        # Proteção
        if not request.user.is_authenticated:
            return redirect("login")

        return self.get_response(request)