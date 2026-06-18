"""Context processors: dados disponíveis em todos os templates."""
from .models import ConfiguracaoSingleton


def global_context(request):
    return {
        "config_sistema": ConfiguracaoSingleton.get(),
        "app_name": "Estoque Cozinha",
    }
