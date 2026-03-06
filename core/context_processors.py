from movimentacoes.models import SolicitacaoVeiculo

def solicitacoes_sidebar(request):
    if not request.user.is_authenticated:
        return {}

    perfil = getattr(request.user, "perfilusuario", None)

    # Apenas gestor e ADM têm contador de aprovações
    if perfil and perfil.nivel in ["gestor", "adm"]:

        # ADM vê todas solicitações pendentes
        pendentes = SolicitacaoVeiculo.objects.filter(status="PENDENTE")

        # Gestor vê apenas solicitações do contrato dele
        if perfil.nivel == "gestor":
            pendentes = pendentes.filter(
                veiculo__contrato_id=perfil.contrato_id
            )

        return {
            "pendentes_aprovacao": pendentes.count()
        }

    return {}
