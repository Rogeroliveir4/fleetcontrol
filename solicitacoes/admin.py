from django.contrib import admin
from .models import SolicitacaoVeiculo

@admin.register(SolicitacaoVeiculo)
class SolicitacaoVeiculoAdmin(admin.ModelAdmin):
    list_display = ("id", "veiculo", "motorista", "status", "contrato", "previsao_retorno")
    list_filter = ("status", "contrato")
    search_fields = ("veiculo__placa", "motorista__nome", "destino")
