from django.urls import path
from . import views

urlpatterns = [
    path('crear/', views.crear_solicitud_view, name='crear_solicitud'),
    path('lista/', views.listar_solicitudes_view, name='listar_solicitudes'),
    path('<int:solicitud_id>/', views.solicitud_detalle_view, name='solicitud_detalle'),
    path('documento/asesor/<int:documento_id>/eliminar/', views.eliminar_documento_asesor_view, name='eliminar_documento_asesor'),
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
    path('solicitud/<int:solicitud_id>/enviar_director/', views.enviar_a_director_view, name='enviar_a_director'),
    path('solicitud/<int:solicitud_id>/devolver_final/', views.devolver_docs_finales_view, name='devolver_docs_finales'),
    path('director/escritorio/', views.director_escritorio_view, name='director_escritorio'),
    path('director/parametros/', views.gestion_parametros_view, name='gestion_parametros'),
    path('director/pendientes/', views.director_pendientes_view, name='director_pendientes'),
    path('director/solicitud/<int:solicitud_id>/', views.director_detalle_solicitud_view, name='director_detalle_solicitud'),
    path('director/solicitud/<int:solicitud_id>/aprobar/', views.aprobar_credito_final_view, name='aprobar_credito_final'),
    path('director/solicitud/<int:solicitud_id>/rechazar/', views.rechazar_credito_final_view, name='rechazar_credito_final'),
    path('director/historial/', views.historial_completo_view, name='historial_completo'),
    path('documento/analista/<int:documento_id>/eliminar/', views.eliminar_documento_analista_view, name='eliminar_documento_analista'),
    path('analista/historial/<int:solicitud_id>/', views.analista_detalle_historial_view, name='analista_detalle_historial'),
        # --- NUEVAS URLs para Gestión de Usuarios ---
    path('director/usuarios/', views.gestion_usuarios_view, name='gestion_usuarios'),
    path('director/usuarios/<str:rol>/', views.gestion_rol_view, name='gestion_rol'),
    path('director/usuarios/<str:rol>/listar/', views.listar_usuarios_por_rol_view, name='listar_usuarios'),
    path('director/usuarios/<str:rol>/crear/', views.crear_usuario_rol_view, name='crear_usuario'),
    path('director/usuarios/eliminar/<int:usuario_id>/', views.eliminar_usuario_view, name='eliminar_usuario'),


]