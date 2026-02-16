# creditos/urls_publico.py
"""
URLs para el flujo público de solicitud de crédito y área privada del aspirante.
"""
from django.urls import path
from . import views_publico

urlpatterns = [
    # === FLUJO PÚBLICO (sin autenticación) ===
    path('', views_publico.aplicar_credito_view, name='aplicar_credito'),
    path('rechazado/<int:solicitud_id>/', views_publico.aplicar_rechazado_view, name='aplicar_rechazado'),
    path('registro/<str:token>/', views_publico.aspirante_registro_view, name='aspirante_registro'),

    # === ÁREA PRIVADA DEL ASPIRANTE (requiere autenticación) ===
    path('mi-solicitud/', views_publico.aspirante_escritorio_view, name='aspirante_escritorio'),
    path('mi-solicitud/subir/', views_publico.aspirante_subir_documento_view, name='aspirante_subir_documento'),
    path('mi-solicitud/enviar/', views_publico.aspirante_enviar_documentos_view, name='aspirante_enviar_documentos'),
    path('mi-solicitud/documento/<int:documento_id>/eliminar/', views_publico.aspirante_eliminar_documento_view, name='aspirante_eliminar_documento'),
    path('mi-solicitud/documento/<int:documento_id>/corregir/', views_publico.aspirante_corregir_documento_view, name='aspirante_corregir_documento'),
]
