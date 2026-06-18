"""Management command: python manage.py gerar_alertas"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Gera alertas de estoque (baixo, ruptura, vencimento, excesso)"

    def handle(self, *args, **options):
        from intelligence.analises import gerar_alertas
        criados = gerar_alertas()
        self.stdout.write(self.style.SUCCESS(f"Alertas criados: {criados}"))
