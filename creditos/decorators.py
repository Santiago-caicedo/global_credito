from django.core.exceptions import PermissionDenied
from functools import wraps

from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.shortcuts import redirect
from functools import wraps

def role_required(allowed_roles=[]):
    """
    Decorador genérico que comprueba si un usuario tiene uno de los roles permitidos.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # Si el usuario no está autenticado o no tiene un perfil, denegar acceso.
            if not request.user.is_authenticated or not hasattr(request.user, 'perfil'):
                raise PermissionDenied

            # Si el rol del usuario no está en la lista de roles permitidos, denegar acceso.
            if request.user.perfil.rol not in allowed_roles:
                messages.error(request, "No tiene permiso para acceder a esta página.")
                # Redirigir a una página segura, como el login o un dashboard principal
                return redirect('login') 
            
            # Si pasa todas las comprobaciones, ejecutar la vista original.
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

# Creamos decoradores específicos para cada rol usando el genérico
aspirante_required = role_required(allowed_roles=['ASPIRANTE'])
analista_required = role_required(allowed_roles=['ANALISTA'])
director_required = role_required(allowed_roles=['DIRECTOR'])