# contas/urls.py
from django.urls import path, include
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # URLs para recuperação de senha
    path('password-reset/', views.password_reset_request, name='password_reset'),
    
    # Views padrão do Django para os outros passos
    path('password-reset/done/', 
            auth_views.PasswordResetDoneView.as_view(
            template_name='contas/password_reset_done.html'
            ), 
            name='password_reset_done'),
    
    path('password-reset-confirm/<uidb64>/<token>/', 
            auth_views.PasswordResetConfirmView.as_view(
                template_name='contas/password_reset_confirm.html',
                success_url='/password-reset-complete/'
            ), 
            name='password_reset_confirm'),
    
    path('password-reset-complete/', 
        auth_views.PasswordResetCompleteView.as_view(
            template_name='contas/password_reset_complete.html'
        ), 
        name='password_reset_complete'),
]