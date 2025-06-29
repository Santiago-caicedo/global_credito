from django.urls import path
from . import views

urlpatterns = [
    path('crear/', views.crear_solicitud_view, name='crear_solicitud'),
    path('lista/', views.listar_solicitudes_view, name='listar_solicitudes'),
    path('<int:solicitud_id>/', views.solicitud_detalle_view, name='solicitud_detalle'),
    path('<int:solicitud_id>/enviar_asignacion/', views.enviar_a_asignacion_view, name='enviar_a_asignacion'),
    path('analista/caso_activo/', views.analista_caso_activo_view, name='analista_caso_activo'),
    path('solicitud/<int:solicitud_id>/preaprobar/', views.preaprobar_solicitud_view, name='preaprobar_solicitud'),
    path('solicitud/<int:solicitud_id>/rechazar/', views.rechazar_solicitud_view, name='rechazar_solicitud'),
    path('solicitud/<int:solicitud_id>/capacidad_pago/', views.capacidad_pago_view, name='capacidad_pago'),
    path('documento/<int:documento_id>/validar/', views.validar_documento_view, name='validar_documento'),
    path('solicitud/<int:solicitud_id>/devolver/', views.devolver_a_asesor_view, name='devolver_a_asesor'),
    path('documento/<int:documento_id>/corregir/', views.corregir_documento_view, name='corregir_documento'),
    path('solicitud/<int:solicitud_id>/enviar_docs_finales/', views.enviar_para_documentos_finales_view, name='enviar_para_documentos_finales'),
    path('solicitud/<int:solicitud_id>/enviar_validacion/', views.enviar_a_validacion_final_view, name='enviar_a_validacion_final'),
    path('solicitud/<int:solicitud_id>/validacion_final/', views.validacion_final_view, name='validacion_final'),
    path('analista/escritorio/', views.analista_escritorio_view, name='analista_escritorio'),
    path('analista/historial/', views.historial_analista_view, name='historial_analista'),


]