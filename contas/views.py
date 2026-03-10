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
            data = password_reset_form.cleaned_data['email']
            
            # Busca usuários pelo email
            associated_users = User.objects.filter(Q(email=data))
            
            if associated_users.exists():
                for user in associated_users:
                    try:
                        # Configurar email
                        subject = "Redefinição de senha - FleetControl"
                        
                        # Gerar token e uid
                        token = default_token_generator.make_token(user)
                        uid = urlsafe_base64_encode(force_bytes(user.pk))
                        
                        # Construir URL completa
                        protocol = 'https' if request.is_secure() else 'http'
                        domain = request.get_host()
                        reset_url = f"{protocol}://{domain}/password-reset-confirm/{uid}/{token}/"
                        
                        # Contexto para o template
                        context = {
                            'user': user,
                            'reset_url': reset_url,
                            'protocol': protocol,
                            'domain': domain,
                            'uid': uid,
                            'token': token,
                        }
                        
                        # Renderizar templates
                        html_message = render_to_string(
                            'contas/password_reset_email.html', 
                            context
                        )
                        
                        # Texto simples (IMPORTANTE para evitar spam)
                        plain_message = f"""
                        Olá {user.get_full_name() or user.username},
                        
                        Recebemos uma solicitação para redefinir a senha da sua conta no FleetControl.
                        
                        Para redefinir sua senha, clique no link abaixo:
                        {reset_url}
                        
                        Este link é válido por 24 horas.
                        
                        Se você não solicitou esta redefinição, ignore este email.
                        
                        Atenciosamente,
                        Equipe FleetControl
                        """
                        
                        # Enviar email
                        send_mail(
                            subject=subject,
                            message=plain_message,
                            from_email=None,  # Usa DEFAULT_FROM_EMAIL do settings.py
                            recipient_list=[user.email],
                            html_message=html_message,
                            fail_silently=False,
                        )
                        
                        # Log simples (opcional)
                        print(f"[INFO] Email de recuperação enviado para {user.email}")
                        
                    except Exception as e:
                        print(f"[ERRO] Erro ao enviar email para {user.email}: {e}")
                        messages.error(
                            request, 
                            "Ocorreu um erro ao enviar o email. Tente novamente."
                        )
                        return render(request, "contas/password_reset.html", 
                                {"form": password_reset_form})
                
                # Sucesso - redireciona para página de confirmação
                messages.success(
                    request,
                    "Se o email estiver cadastrado, você receberá instruções em alguns minutos."
                )
                return redirect("password_reset_done")
            
            else:
                # Email não encontrado - mensagem genérica por segurança
                messages.info(
                    request,
                    "Se o email estiver cadastrado, você receberá instruções para redefinir sua senha em alguns minutos."
                )
                return redirect("password_reset_done")
    
    else:
        # GET request - mostrar formulário vazio
        password_reset_form = PasswordResetForm()
    
    return render(request, "contas/password_reset.html", 
                {"form": password_reset_form})