# creditos/admin.py
from django.contrib import admin
from .models import SolicitudCredito, Referencia, HistorialEstado, Documento

admin.site.register(SolicitudCredito)
admin.site.register(Referencia)
admin.site.register(HistorialEstado)
admin.site.register(Documento)