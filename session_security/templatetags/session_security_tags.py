from django import template

from session_security.settings import EXPIRE_AFTER, REDIRECT_TO_LOGOUT, WARN_AFTER

register = template.Library()


@register.filter
def expire_after(request):
    return EXPIRE_AFTER


@register.filter
def warn_after(request):
    return WARN_AFTER


@register.filter
def redirect_to_logout(request):
    return REDIRECT_TO_LOGOUT
