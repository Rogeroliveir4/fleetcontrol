from .models import HistoricoKM
from django.utils import timezone
from datetime import timedelta
from veiculos.models import Veiculo
from django.core.mail import EmailMultiAlternatives

def atualizar_km_veiculo(veiculo, km_novo, origem="RETORNO_PORTARIA"):
    km_antigo = veiculo.km_atual

    if km_novo < km_antigo:
        raise ValueError("O KM informado é menor que o KM atual.")

    # Atualiza campos do veículo
    veiculo.km_anterior = km_antigo      # registra o anterior
    veiculo.km_atual = km_novo           # atualiza real
    veiculo.save()

    # Cria histórico corporativo
    HistoricoKM.objects.create(
        veiculo=veiculo,
        km_anterior=km_antigo,
        km_novo=km_novo,
        origem=origem
    )


# ALERTA DE  LICENCIAMENTO COM VENCIMENTO PRÓXIMO 
def enviar_alerta_licenciamento():

    hoje = timezone.now().date()
    limite = hoje + timedelta(days=30)

    veiculos = Veiculo.objects.filter(
        ativo=True,
        licenciamento_vencimento__isnull=False,
        licenciamento_vencimento__gte=hoje,
        licenciamento_vencimento__lte=limite
    ).order_by('licenciamento_vencimento')

    if not veiculos.exists():
        return

    #  Montar tabela HTML
    linhas = ""

    for v in veiculos:
        dias = (v.licenciamento_vencimento - hoje).days

        if dias <= 7:
            cor = "#fee2e2"
            status = f"🔴 URGENTE ({dias} dias)"
        elif dias <= 15:
            cor = "#fff7ed"
            status = f"🟠 Atenção ({dias} dias)"
        else:
            cor = "#fefce8"
            status = f"🟡 Próximo ({dias} dias)"

        linhas += f"""
        <tr style="background:{cor}; border-bottom:1px solid #eee;">
            <td style="padding:10px;">{v.tag_interna or '-'}</td>
            <td style="padding:10px;">{v.placa}</td>
            <td style="padding:10px;">{v.renavam or '-'}</td>
            <td style="padding:10px;">{v.licenciamento_vencimento.strftime('%d/%m/%Y')}</td>
            <td style="padding:10px; font-weight:bold;">{status}</td>
        </tr>
        """

    html = f"""
<div style="font-family: Arial, sans-serif; background:#f4f6f8; padding:20px;">
    
    <!-- CONTAINER -->
    <div style="max-width:800px; margin:auto; background:white; border-radius:8px; overflow:hidden; box-shadow:0 2px 8px rgba(0,0,0,0.05);">
        
        <!-- HEADER -->
        <div style="background:#2f6f55; padding:20px; text-align:center;">
            <h1 style="color:white; margin:0;">Rota 360</h1>
            <p style="color:#cfe7dd; margin:5px 0 0;">Alerta de Licenciamento</p>
        </div>

        <!-- BODY -->
        <div style="padding:20px;">
            
            <h2 style="margin-top:0;">🚨 Veículos com Licenciamento Próximo do Vencimento</h2>
            <p style="color:#555;">
                Foram encontrados veículos com vencimento nos próximos <strong>30 dias</strong>.
            </p>

            <!-- TABELA -->
            <table style="width:100%; border-collapse:collapse; margin-top:15px;">
                <thead>
                    <tr style="background:#f1f5f9; text-align:left;">
                        <th style="padding:10px;">TAG</th>
                        <th style="padding:10px;">PLACA</th>
                        <th style="padding:10px;">RENAVAM</th>
                        <th style="padding:10px;">VENCIMENTO</th>
                        <th style="padding:10px;">STATUS</th>
                    </tr>
                </thead>
                <tbody>
                    {linhas}
                </tbody>
            </table>

        </div>
        <br>
        <br>
        <!-- FOOTER -->
        <div style="background:#f9fafb; padding:15px; text-align:center; font-size:12px; color:#777;">
            Sistema de Gestão de Pátio<br>
            Este é um email automático, não responda.<br><br>
            © 2026 Rota 360clear
        </div>

    </div>
</div>
"""

    from django.contrib.auth.models import User

    gestores = User.objects.filter(
        perfilusuario__nivel__in=["gestor", "adm"],
        is_active=True
    )

    emails = [u.email for u in gestores if u.email]

    if not emails:
        return

    email = EmailMultiAlternatives(
        subject=" Alerta de Licenciamento de Veículos",
        body="Existem veículos com vencimento próximo.",
        to=emails,
    )

    email.attach_alternative(html, "text/html")
    email.send()