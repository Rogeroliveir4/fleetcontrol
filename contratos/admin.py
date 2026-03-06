from django.contrib import admin
from .models import Contrato

@admin.register(Contrato)
class ContratoAdmin(admin.ModelAdmin):
    list_display = ("nome", "cliente", "ativo")
    search_fields = ("nome", "cliente")
    list_filter = ("ativo",)
