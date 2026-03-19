from django.urls import path
from . import views

urlpatterns = [
    # === ANALISTA ===
    path('analista/escritorio/', views.analista_escritorio_view, name='analista_escritorio'),
    path('analista/caso_activo/', views.analista_caso_activo_view, name='analista_caso_activo'),
    path('analista/historial/', views.historial_analista_view, name='historial_analista'),
    path('analista/historial/<int:solicitud_id>/', views.analista_detalle_historial_view, name='analista_detalle_historial'),

    # Acciones del analista sobre solicitudes
    path('solicitud/<int:solicitud_id>/preaprobar/', views.preaprobar_solicitud_view, name='preaprobar_solicitud'),
    path('solicitud/<int:solicitud_id>/rechazar/', views.rechazar_solicitud_view, name='rechazar_solicitud'),
    path('solicitud/<int:solicitud_id>/capacidad_pago/', views.capacidad_pago_view, name='capacidad_pago'),
    path('solicitud/<int:solicitud_id>/devolver/', views.devolver_a_aspirante_view, name='devolver_a_aspirante'),
    path('solicitud/<int:solicitud_id>/enviar_docs_finales/', views.enviar_para_documentos_finales_view, name='enviar_para_documentos_finales'),
    path('solicitud/<int:solicitud_id>/validacion_final/', views.validacion_final_view, name='validacion_final'),
    path('solicitud/<int:solicitud_id>/enviar_director/', views.enviar_a_director_view, name='enviar_a_director'),
    path('solicitud/<int:solicitud_id>/devolver_final/', views.devolver_docs_finales_view, name='devolver_docs_finales'),

    # Acciones sobre documentos (analista)
    path('documento/<int:documento_id>/validar/', views.validar_documento_view, name='validar_documento'),
    path('documento/analista/<int:documento_id>/eliminar/', views.eliminar_documento_analista_view, name='eliminar_documento_analista'),

    # === DIRECTOR ===
    path('director/escritorio/', views.director_escritorio_view, name='director_escritorio'),
    path('director/parametros/', views.gestion_parametros_view, name='gestion_parametros'),
    path('director/pendientes/', views.director_pendientes_view, name='director_pendientes'),
    path('director/historial/', views.historial_completo_view, name='historial_completo'),
    path('director/solicitud/<int:solicitud_id>/', views.director_detalle_solicitud_view, name='director_detalle_solicitud'),
    path('director/solicitud/<int:solicitud_id>/aprobar/', views.aprobar_credito_final_view, name='aprobar_credito_final'),
    path('director/solicitud/<int:solicitud_id>/rechazar/', views.rechazar_credito_final_view, name='rechazar_credito_final'),
    path('director/solicitud/<int:solicitud_id>/desembolsar/', views.desembolsar_credito_view, name='desembolsar_credito'),

    # Gestion de usuarios (Director)
    path('director/usuarios/', views.gestion_usuarios_view, name='gestion_usuarios'),
    path('director/usuarios/<str:rol>/', views.gestion_rol_view, name='gestion_rol'),
    path('director/usuarios/<str:rol>/listar/', views.listar_usuarios_por_rol_view, name='listar_usuarios'),
    path('director/usuarios/<str:rol>/crear/', views.crear_usuario_rol_view, name='crear_usuario'),
    path('director/usuarios/eliminar/<int:usuario_id>/', views.eliminar_usuario_view, name='eliminar_usuario'),
]
