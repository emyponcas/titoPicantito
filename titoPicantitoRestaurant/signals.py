from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from .models import HistorialLogin


@receiver(user_logged_in)
def register_login(sender, user, request, **kwargs):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')

    HistorialLogin.objects.create(
        usuario=user,
        direccion_ip=ip,
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )