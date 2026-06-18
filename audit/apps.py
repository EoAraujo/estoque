from django.apps import AppConfig


class AuditConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "audit"
    verbose_name = "Auditoria"

    def ready(self):
        # Importa aqui para garantir que os signals estejam conectados
        # depois que todos os modelos foram registrados.
        from . import signals  # noqa: F401

