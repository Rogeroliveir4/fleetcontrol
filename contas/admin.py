from django.contrib import admin
from .models import PerfilUsuario

@admin.register(PerfilUsuario)
class PerfilUsuarioAdmin(admin.ModelAdmin):
    list_display = ("nome_exibicao", "user", "nivel")
    search_fields = ("nome_exibicao", "user__username")
