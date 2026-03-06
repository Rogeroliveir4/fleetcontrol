from django.apps import AppConfig


class MotoristasConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'motoristas'

    def ready(self):
        import motoristas.signals
