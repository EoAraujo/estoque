"""
Funções utilitárias para geração de relatórios.

Centraliza formatação e geração de arquivos Excel/PDF.
"""
from datetime import date, datetime
from decimal import Decimal


def fmt_decimal(value, places=2):
    """Formata Decimal para string com N casas, tolerando None."""
    if value is None or value == "":
        return ""
    if isinstance(value, Decimal):
        return f"{value:.{places}f}"
    return str(value)


def fmt_date(value):
    """Formata data/datetime em dd/mm/yyyy; '' se None."""
    if not value:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y %H:%M")
    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")
    return str(value)


def apply_borders(ws, cell_range):
    """Aplica bordas finas a um range do openpyxl."""
    from openpyxl.styles import Border, Side

    thin = Side(border_style="thin", color="888888")
    border = Border(top=thin, bottom=thin, left=thin, right=thin)
    for row in ws[cell_range]:
        for cell in row:
            cell.border = border
