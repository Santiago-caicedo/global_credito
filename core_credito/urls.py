from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic.base import RedirectView # Importamos la vista de redirección

urlpatterns = [
    path('admin/', admin.site.urls),
    path('solicitudes/', include('creditos.urls')),
    path('cuentas/', include('usuarios.urls')),

    # --- FLUJO PÚBLICO Y ÁREA DEL ASPIRANTE ---
    path('aplicar/', include('creditos.urls_publico')),

    # Redirige la raíz del sitio al formulario público de solicitud
    path('', RedirectView.as_view(url='/aplicar/', permanent=False)),
    path('__debug__/', include('debug_toolbar.urls')),
]


if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
