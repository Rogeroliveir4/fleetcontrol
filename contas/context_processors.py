from .models import PerfilUsuario
from solicitacoes.models import SolicitacaoVeiculo

def perfil_usuario(request):
    if not request.user.is_authenticated:
        return {}
    perfil = PerfilUsuario.objects.filter(user=request.user).first()
    return {"perfilusuario": perfil}



def pendencias_gestor(request):
    if not request.user.is_authenticated:
        return {}

    perfil = getattr(request.user, "perfilusuario", None)

    # Apenas gestor recebe notificações
    if not perfil or perfil.nivel != "gestor":
        return {}

    pendentes = SolicitacaoVeiculo.objects.filter(
        contrato=perfil.contrato,
        status="PENDENTE"
    ).count()

    return {"pendentes_gestor": pendentes}

