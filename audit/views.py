"""Views de auditoria (consulta de logs)."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import redirect, render

from .models import LogAuditoria


@login_required
def log_list(request):
    if not request.user.is_staff:
        messages.error(request, "Sem permissão para consultar auditoria.")
        return redirect("core:dashboard")

    qs = LogAuditoria.objects.select_related("usuario").all()

    busca = request.GET.get("q", "").strip()
    acao = request.GET.get("acao", "").strip()
    modelo = request.GET.get("modelo", "").strip()
    usuario = request.GET.get("usuario", "").strip()

    if busca:
        qs = qs.filter(
            Q(objeto_repr__icontains=busca) |
            Q(objeto_id__icontains=busca) |
            Q(url__icontains=busca)
        )
    if acao:
        qs = qs.filter(acao=acao)
    if modelo:
        qs = qs.filter(modelo=modelo)
    if usuario:
        qs = qs.filter(usuario__username__icontains=usuario)

    paginator = Paginator(qs, 50)
    page = paginator.get_page(request.GET.get("page"))

    return render(request, "audit/log_list.html", {
        "page": page,
        "acoes": LogAuditoria.ACAO_CHOICES,
        "filtros": {
            "q": busca, "acao": acao, "modelo": modelo, "usuario": usuario,
        },
    })
