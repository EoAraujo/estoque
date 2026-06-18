"""
Sinais (signals) de auditoria.

Conecta handlers para:
- Login / logout (do Django auth)
- Post-save / post-delete em modelos monitorados (criar logs de CRUD)
"""
import threading

from django.apps import apps
from django.contrib.auth.signals import (
    user_logged_in, user_logged_out, user_login_failed,
)
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.forms.models import model_to_dict

from .middleware import get_current_request
from .models import LogAuditoria


# ============================================================================
# 1) Signals de autenticação
# ============================================================================
@receiver(user_logged_in)
def _log_login(sender, request, user, **kwargs):
    LogAuditoria.objects.create(
        usuario=user, acao="LOGIN",
        ip=_ip(request), user_agent=_ua(request),
        url=(request.path if request else ""),
    )


@receiver(user_logged_out)
def _log_logout(sender, request, user, **kwargs):
    LogAuditoria.objects.create(
        usuario=user, acao="LOGOUT",
        ip=_ip(request), user_agent=_ua(request),
        url=(request.path if request else ""),
    )


@receiver(user_login_failed)
def _log_login_failed(sender, credentials, request, **kwargs):
    LogAuditoria.objects.create(
        acao="LOGIN",
        objeto_repr=f"Falha de login: {credentials.get('username', '?')}",
        ip=_ip(request), user_agent=_ua(request),
        url=(request.path if request else ""),
    )


def _ip(request):
    if not request:
        return None
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _ua(request):
    if not request:
        return ""
    return request.META.get("HTTP_USER_AGENT", "")[:255]


# ============================================================================
# 2) Signals de modelos (CRUD)
# ============================================================================
APPS_MONITORADAS = {"core", "stock", "accounts"}
MODELOS_IGNORADOS = {"LogAuditoria", "Alerta", "UserProfile"}


def _usuario_request():
    req = get_current_request()
    if not req:
        return None
    user = getattr(req, "user", None)
    if user and user.is_authenticated:
        return user
    return None


def _serializar(instance):
    try:
        d = model_to_dict(instance)
        return {
            k: (str(v) if not isinstance(v, (str, int, float, bool, list, dict, type(None))) else v)
            for k, v in d.items()
        }
    except Exception:
        return {"repr": str(instance)}


def _criar_log(*, acao, instance, dados_anteriores=None, dados_novos=None):
    try:
        LogAuditoria.objects.create(
            usuario=_usuario_request(),
            acao=acao,
            modelo=type(instance).__name__,
            objeto_id=str(instance.pk),
            objeto_repr=str(instance)[:255],
            dados_anteriores=dados_anteriores or {},
            dados_novos=dados_novos or {},
            ip=_ip(get_current_request()),
            user_agent=_ua(get_current_request()),
            url=(get_current_request().path if get_current_request() else ""),
        )
    except Exception:
        # Auditoria nunca pode quebrar a operação principal
        pass


def _conectar_signals_de_modelos():
    """Conecta post_save/post_delete em todos os modelos das apps monitoradas."""
    for model in apps.get_models():
        if model._meta.app_label not in APPS_MONITORADAS:
            continue
        if model.__name__ in MODELOS_IGNORADOS:
            continue

        @receiver(post_save, sender=model, weak=False, dispatch_uid=f"audit_save_{model._meta.label}")
        def _post_save(sender, instance, created, **kwargs):
            _criar_log(
                acao="CRIAR" if created else "EDITAR",
                instance=instance,
                dados_novos=_serializar(instance),
            )

        @receiver(post_delete, sender=model, weak=False, dispatch_uid=f"audit_del_{model._meta.label}")
        def _post_delete(sender, instance, **kwargs):
            _criar_log(
                acao="EXCLUIR",
                instance=instance,
                dados_anteriores=_serializar(instance),
            )


_conectar_signals_de_modelos()
