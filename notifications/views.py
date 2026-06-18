"""
Views de notificações push (Fase 5).

Endpoints:
- GET  /notificacoes/vapid-key/         → retorna a chave pública VAPID
- POST /notificacoes/subscribe/         → salva uma nova subscription
- POST /notificacoes/unsubscribe/       → remove subscription
- POST /notificacoes/test/              → envia um push de teste
"""
import json
import logging

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest, JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_GET, require_POST

from .models import WebPushSubscription
from .vapid import ensure_vapid_keys, get_vapid_public_key, get_vapid_private_key, get_vapid_claims

logger = logging.getLogger(__name__)


@login_required
@require_GET
def vapid_public_key(request):
    """Retorna a chave pública VAPID para o service worker."""
    ensure_vapid_keys()
    return JsonResponse({"publicKey": get_vapid_public_key()})


@login_required
@csrf_protect
@require_POST
def subscribe(request):
    """Registra a subscription do navegador."""
    try:
        data = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return HttpResponseBadRequest("JSON inválido")

    endpoint = data.get("endpoint")
    keys = data.get("keys") or {}
    p256dh = keys.get("p256dh")
    auth = keys.get("auth")
    if not (endpoint and p256dh and auth):
        return HttpResponseBadRequest("Subscription inválida.")

    sub, created = WebPushSubscription.objects.update_or_create(
        endpoint=endpoint,
        defaults={
            "user": request.user,
            "p256dh": p256dh,
            "auth": auth,
            "user_agent": request.META.get("HTTP_USER_AGENT", "")[:255],
            "ativo": True,
        },
    )
    return JsonResponse({
        "ok": True,
        "created": created,
        "id": sub.pk,
    })


@login_required
@csrf_protect
@require_POST
def unsubscribe(request):
    """Remove a subscription."""
    try:
        data = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return HttpResponseBadRequest("JSON inválido")
    endpoint = data.get("endpoint")
    if not endpoint:
        return HttpResponseBadRequest("Endpoint ausente.")
    WebPushSubscription.objects.filter(
        user=request.user, endpoint=endpoint,
    ).delete()
    return JsonResponse({"ok": True})


@login_required
@csrf_protect
@require_POST
def test_push(request):
    """Envia um push de teste para todas as subscriptions do usuário."""
    ensure_vapid_keys()
    title = "Estoque Cozinha · Teste"
    body = "Notificações push estão funcionando! 🎉"
    resultado = enviar_para_usuario(
        request.user, title=title, body=body, url="/",
    )
    return JsonResponse(resultado)


def enviar_para_usuario(user, title, body, url="/", tag="estoque"):
    """Envia push para todas as subscriptions ativas de um usuário."""
    from pywebpush import webpush, WebPushException
    ensure_vapid_keys()

    subs = WebPushSubscription.objects.filter(user=user, ativo=True)
    if not subs.exists():
        return {"ok": False, "enviados": 0, "motivo": "sem subscriptions"}

    payload = json.dumps({
        "title": title,
        "body": body,
        "url": url,
        "tag": tag,
    })
    claims = get_vapid_claims()
    enviados = 0
    falhas = []
    for sub in subs:
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
                },
                data=payload,
                vapid_private_key=get_vapid_private_key(),
                vapid_claims=claims,
            )
            enviados += 1
        except WebPushException as e:
            falhas.append({"endpoint": sub.endpoint[:60], "erro": str(e)})
            # Remove subscription inválida (410 Gone)
            if "410" in str(e) or "404" in str(e):
                sub.ativo = False
                sub.save(update_fields=["ativo"])
    return {
        "ok": True,
        "enviados": enviados,
        "falhas": falhas,
        "total": subs.count(),
    }
