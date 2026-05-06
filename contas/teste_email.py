# test_email.py
import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'seuprojeto.settings')
django.setup()

from django.core.mail import send_mail

print("🧪 Testando configuração do SendGrid...")
print("=" * 50)

try:
    # Enviar email de teste
    send_mail(
        subject='✅ Teste SendGrid - Rota 360',
        message='Olá! Este é um teste do sistema Rota 360.\n\nSe recebeu este email, seu SendGrid está configurado corretamente!',
        from_email=None,  # Usará DEFAULT_FROM_EMAIL automaticamente
        recipient_list=['rogerquat13@gmail.com'],  # COLOCA SEU EMAIL AQUI
        html_message='''
        <div style="font-family: Arial, sans-serif; padding: 20px; background: #f5f5f5;">
            <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 10px; padding: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                <h2 style="color: #2b654d; border-bottom: 3px solid #49b48b; padding-bottom: 10px;">🎉 Teste Bem-Sucedido!</h2>
                <p>Seu <strong>SendGrid</strong> está funcionando perfeitamente com o <strong>Django</strong>!</p>
                
                <div style="background: #f0f9f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <p style="margin: 0;">✅ Email remetente autenticado</p>
                    <p style="margin: 5px 0;">✅ API Key configurada</p>
                    <p style="margin: 0;">✅ SMTP funcionando</p>
                </div>
                
                <p>Agora você pode implementar o sistema completo de recuperação de senha!</p>
                
                <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; text-align: center;">
                    <p style="color: #666; font-size: 12px;">Rota 360 - Sistema de Gestão de Frotas</p>
                </div>
            </div>
        </div>
        ''',
        fail_silently=False,
    )
    
    print("✅ Email enviado com sucesso!")
    print("📧 Verifique sua caixa de entrada")
    print("   (pode levar alguns minutos, verifique também a pasta de spam)")
    
except Exception as e:
    print(f"❌ ERRO ao enviar email: {type(e).__name__}")
    print(f"   Mensagem: {str(e)}")
    print("\n🔍 Verifique:")
    print("   1. API Key está correta no settings.py")
    print("   2. EMAIL_HOST_USER = 'apikey' (exatamente assim)")
    print("   3. Email remetente está VERIFICADO no SendGrid")
    print("   4. Não há espaços extras na API Key")