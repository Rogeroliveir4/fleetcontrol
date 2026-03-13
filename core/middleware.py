from django.shortcuts import redirect
from django.urls import reverse

class LoginRequiredMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

        # Rotas que podem ser acessadas sem login
        self.public_urls = [
            reverse("login"),
            reverse("password_reset"),
            reverse("password_reset_done"),
        ]

    def __call__(self, request):

        # Ignorar arquivos estáticos e media
        if request.path.startswith("/static/") or request.path.startswith("/media/"):
            return self.get_response(request)

        # Se não estiver autenticado e tentar acessar rota protegida
        if not request.user.is_authenticated and request.path not in self.public_urls:
            return redirect("login")

        response = self.get_response(request)
        return response