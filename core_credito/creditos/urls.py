from django.urls import path
from . import views

urlpatterns = [
    path('crear/', views.crear_solicitud_view, name='crear_solicitud'),
    path('lista/', views.listar_solicitudes_view, name='listar_solicitudes'),
    path('<int:solicitud_id>/', views.solicitud_detalle_view, name='solicitud_detalle'),
    path('<int:solicitud_id>/enviar_asignacion/', views.enviar_a_asignacion_view, name='enviar_a_asignacion'),
    path('analista/dashboard/', views.analista_dashboard_view, name='analista_dashboard'),

]