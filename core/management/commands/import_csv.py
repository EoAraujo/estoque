"""
Comando para importar produtos de um arquivo CSV.

Uso:
    python manage.py import_csv --arquivo "caminho/do/arquivo.csv"
    python manage.py import_csv --arquivo "caminho/do/arquivo.csv" --dry-run
"""
import csv
import os
import unicodedata

from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Categoria, Produto


CATEGORIA_MAP = {
    "sucos": "Bebidas",
    "bebidas": "Bebidas",
    "estocavel": "Gerais",
    "estoque": "Gerais",
    "proteina": "Carnes e Frios",
    "carnes": "Carnes e Frios",
    "limpeza": "Limpeza",
    "embalagem": "Embalagens",
    "embalagens": "Embalagens",
}

CATEGORIA_CORES = {
    "Bebidas": "#3B82F6",
    "Gerais": "#6B7280",
    "Carnes e Frios": "#EF4444",
    "Limpeza": "#10B981",
    "Embalagens": "#F59E0B",
}


def strip_accents(s):
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def read_csv(filepath):
    for enc in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
        try:
            with open(filepath, "r", encoding=enc) as f:
                reader = csv.DictReader(f, delimiter=";")
                rows = list(reader)
            if rows:
                return rows, enc
        except (UnicodeDecodeError, UnicodeError):
            continue
    return None, None


class Command(BaseCommand):
    help = "Importa produtos de um arquivo CSV"

    def add_arguments(self, parser):
        parser.add_argument("--arquivo", required=True)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        arquivo = options["arquivo"]
        dry_run = options["dry_run"]

        if not os.path.exists(arquivo):
            self.stderr.write(self.style.ERROR(f"Arquivo nao encontrado: {arquivo}"))
            return

        produtos_csv, encoding = read_csv(arquivo)
        if not produtos_csv:
            self.stderr.write(self.style.ERROR("Nao foi possivel ler o CSV"))
            return

        self.stdout.write(f"Encoding: {encoding} | Registros: {len(produtos_csv)}")

        headers = list(produtos_csv[0].keys())
        self.stdout.write(f"Headers: {headers}")

        stats = {"criados": 0, "atualizados": 0, "erros": 0}

        categorias = {}
        for nome_csv, nome_sistema in CATEGORIA_MAP.items():
            cat, _ = Categoria.objects.get_or_create(
                nome=nome_sistema,
                defaults={"cor": CATEGORIA_CORES.get(nome_sistema, "#6B7280")},
            )
            categorias[nome_csv] = cat

        unidade_map = {
            "PC": "PC", "KG": "KG", "CX": "CX", "L": "L",
            "UN": "UN", "PAC": "PAC", "ROL": "ROL",
        }

        if dry_run:
            sid = transaction.savepoint()

        for row in produtos_csv:
            vals = list(row.values())
            codigo = (vals[0] or "").strip()
            categoria_raw = (vals[1] or "").strip()
            descricao = (vals[2] or "").strip()
            unidade = (vals[3] or "").strip().upper()
            centro_custo = (vals[4] or "").strip()

            if not codigo or not descricao:
                stats["erros"] += 1
                continue

            unidade_sys = unidade_map.get(unidade, "UN")

            cat_norm = strip_accents(categoria_raw).lower().strip()
            categoria_obj = categorias.get(cat_norm)

            if not categoria_obj:
                for key, cat in categorias.items():
                    if key in cat_norm or cat_norm.startswith(key[:4]):
                        categoria_obj = cat
                        break

            if not categoria_obj:
                self.stderr.write(f"Categoria '{categoria_raw}' -> '{cat_norm}' nao mapeada. Produto: {codigo}")
                stats["erros"] += 1
                continue

            observacoes = f"Centro de custo: {centro_custo}" if centro_custo else ""

            try:
                produto, created = Produto.objects.update_or_create(
                    codigo_interno=codigo,
                    defaults={
                        "nome": descricao,
                        "categoria": categoria_obj,
                        "unidade_medida": unidade_sys,
                        "observacoes": observacoes,
                        "controla_validade": True,
                    },
                )
                if created:
                    stats["criados"] += 1
                else:
                    stats["atualizados"] += 1
            except Exception as e:
                self.stderr.write(f"Erro produto {codigo}: {e}")
                stats["erros"] += 1

        if dry_run:
            transaction.savepoint_rollback(sid)

        self.stdout.write("")
        self.stdout.write("=" * 50)
        self.stdout.write("RELATORIO DE IMPORTACAO")
        self.stdout.write("=" * 50)
        self.stdout.write(f"Criados:    {stats['criados']}")
        self.stdout.write(f"Atualizados: {stats['atualizados']}")
        self.stdout.write(f"Erros:      {stats['erros']}")
        self.stdout.write("=" * 50)

        if dry_run:
            self.stdout.write("[DRY RUN] Nenhuma alteracao salva.")
