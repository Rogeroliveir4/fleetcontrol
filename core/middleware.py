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

    def __call__(self, request):

        # Liberar static e media
        if request.path.startswith("/static/") or request.path.startswith("/media/"):
            return self.get_response(request)

        #  LIBERAR ADMIN (ESSENCIAL)
        if request.path.startswith("/admin/"):
            return self.get_response(request)

        # Proteção padrão
        if not request.user.is_authenticated and request.path not in self.public_urls:
            return redirect("login")

        return self.get_response(request)