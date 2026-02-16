# usuarios/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import PerfilUsuario


@receiver(post_save, sender=PerfilUsuario)
def asignar_solicitud_a_nuevo_analista(sender, instance, created, **kwargs):
    """
    Cuando se crea o actualiza un perfil de analista que está libre,
    intenta asignarle una solicitud en espera.
    """
    # Solo actuar si es un analista y está libre (sin solicitud asignada)
    if instance.rol == PerfilUsuario.ROL_ANALISTA and instance.solicitud_actual is None:
        # Importamos aquí para evitar imports circulares
        from creditos.services import intentar_asignar_solicitud_en_espera

        print(f"Analista {instance.usuario.username} está libre. Buscando solicitudes en espera...")
        intentar_asignar_solicitud_en_espera()
