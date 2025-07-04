
from django.db import models
from django.contrib.auth.models import User
from creditos.models import SolicitudCredito

class PerfilUsuario(models.Model):
    ROL_ASESOR = 'ASESOR'
    ROL_ANALISTA = 'ANALISTA'
    ROL_DIRECTOR = 'DIRECTOR'
    ROLES = [
        (ROL_ASESOR, 'Asesor Comercial'),
        (ROL_ANALISTA, 'Analista de Crédito'),
        (ROL_DIRECTOR, 'Director'),
    ]
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    rol = models.CharField(max_length=10, choices=ROLES)
    telefono = models.CharField("Teléfono", max_length=20, blank=True, null=True)

    # --- NUEVO CAMPO ---
    # Si este campo apunta a una solicitud, el analista está ocupado.
    # Si es NULL, está libre.
    solicitud_actual = models.OneToOneField(
        'creditos.SolicitudCredito',
        on_delete=models.SET_NULL, # Si la solicitud se borra, el analista queda libre
        null=True,
        blank=True,
        related_name='perfil_analista_asignado'
    )
    # -------------------

    def __str__(self):
        return f"{self.usuario.username} - {self.get_rol_display()}"
