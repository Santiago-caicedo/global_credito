from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic.base import RedirectView # Importamos la vista de redirección

urlpatterns = [
    path('admin/', admin.site.urls),
    path('solicitudes/', include('creditos.urls')),
    path('cuentas/', include('usuarios.urls')),
    
    # --- ¡AQUÍ ESTÁ LA CORRECCIÓN! ---
    # Esta línea redirige la raíz del sitio ('/') a la página de login ('/cuentas/login/').
    path('', RedirectView.as_view(url='/cuentas/login/', permanent=True)),
]

# La configuración para servir archivos multimedia se mantiene igual
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
