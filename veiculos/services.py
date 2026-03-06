from .models import HistoricoKM

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
