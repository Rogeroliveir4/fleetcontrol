from django.shortcuts import render, redirect
from contas.models import PerfilUsuario
from veiculos.models import Veiculo
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.shortcuts import render, redirect
from solicitacoes.models import SolicitacaoVeiculo
from movimentacoes.models import Movimentacao
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.template.loader import render_to_string
from django.core.mail import send_mail, BadHeaderError
from django.http import HttpResponse
from django.db.models.query_utils import Q
from django.contrib.auth.models import User
import logging
from django.core.mail import EmailMultiAlternatives

# Configuração de logging (opcional, mas recomendado para produção)
def login_view(request):

    if request.method == "POST":
        usuario = request.POST.get("username")
        senha = request.POST.get("password")

        user = authenticate(request, username=usuario, password=senha)

        if user is not None:
            login(request, user)

            # Obtém o perfil do usuário autenticado
            perfil = user.perfilusuario

            #  1) ADMINISTRADOR – visão completa
            if perfil.nivel == "adm":
                return redirect("dashboard")

            #  2) GESTOR – visão de gestão
            elif perfil.nivel == "gestor":
                return redirect("dashboard_gestor")

            #  3) PORTARIA – visão operacional (SAÍDA)
            elif perfil.nivel == "portaria":
                return redirect("listar_saidas_portaria")   

            #  4) MOTORISTA/SOLICITANTE – visão limitada
            elif perfil.nivel == "basico":
                return redirect("dashboard_motorista")

            # fallback de segurança
            return redirect("dashboard")

        else:
            messages.error(request, "Usuário ou senha incorretos.")

    return render(request, "contas/login.html")



# View para logout
def logout_view(request):
    logout(request)
    return redirect("login")


# View personalizada para solicitação de recuperação de senha
def password_reset_request(request):

    if request.method == "POST":
        password_reset_form = PasswordResetForm(request.POST)

        if password_reset_form.is_valid():
            data = password_reset_form.cleaned_data['email'].strip()

            # Busca usuário pelo email (case insensitive)
            user = User.objects.filter(email__iexact=data).first()

            if user:
                try:
                    subject = "FleetControl - Redefinição de senha da sua conta"

                    # Gerar token e uid
                    token = default_token_generator.make_token(user)
                    uid = urlsafe_base64_encode(force_bytes(user.pk))

                    # Construir URL completa
                    protocol = 'https' if request.is_secure() else 'http'
                    domain = request.get_host()
                    reset_url = f"{protocol}://{domain}/password-reset-confirm/{uid}/{token}/"

                    context = {
                        'user': user,
                        'reset_url': reset_url,
                        'protocol': protocol,
                        'domain': domain,
                        'uid': uid,
                        'token': token,
                    }

                    # Renderizar HTML
                    html_message = render_to_string(
                        'contas/password_reset_email.html',
                        context
                    )

                    # Texto simples (importante para Outlook)
                    plain_message = f"""
Olá {user.get_full_name() or user.username},

Recebemos uma solicitação para redefinir a senha da sua conta no FleetControl.

Acesse o link abaixo para criar uma nova senha:

{reset_url}

Este link é válido por 24 horas.

Se você não solicitou essa redefinição, ignore este email.

Equipe FleetControl
fleetcontrol.app@gmail.com
"""

                    # Enviar email
                    email = EmailMultiAlternatives(
                        subject=subject,
                        body=plain_message,
                        from_email="FleetControl <fleetcontrol.app@gmail.com>",
                        to=[user.email],
                        headers={"Reply-To": "fleetcontrol.app@gmail.com"},
                    )

                    email.attach_alternative(html_message, "text/html")
                    email.send(fail_silently=False)

                    print(f"[INFO] Email de recuperação enviado para {user.email}")

                except Exception as e:
                    print(f"[ERRO] Erro ao enviar email para {user.email}: {e}")
                    messages.error(
                        request,
                        "Ocorreu um erro ao enviar o email. Tente novamente."
                    )
                    return render(
                        request,
                        "contas/password_reset.html",
                        {"form": password_reset_form}
                    )

            # Mensagem genérica (segurança)
            messages.success(
                request,
                "Se o email estiver cadastrado, você receberá instruções em alguns minutos."
            )

            return redirect("password_reset_done")

    else:
        password_reset_form = PasswordResetForm()

    return render(
        request,
        "contas/password_reset.html",
        {"form": password_reset_form}
    )