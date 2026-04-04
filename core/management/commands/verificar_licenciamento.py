from django.core.management.base import BaseCommand
from veiculos.services import enviar_alerta_licenciamento

class Command(BaseCommand):
    help = "Verifica licenciamento e envia alertas"

    def handle(self, *args, **kwargs):
        enviar_alerta_licenciamento()
        self.stdout.write(self.style.SUCCESS("✔ Alertas enviados"))