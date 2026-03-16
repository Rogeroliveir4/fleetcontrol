from django.contrib import admin
from .models import IPVA, Licenciamento, Multa, Manutencao


admin.site.register(IPVA)
admin.site.register(Licenciamento)
admin.site.register(Multa)
admin.site.register(Manutencao)