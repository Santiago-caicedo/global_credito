from django.core.exceptions import PermissionDenied
from functools import wraps

def director_required(view_func):
    """
    Decorador que comprueba si el usuario logueado tiene el rol de DIRECTOR.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated or not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'DIRECTOR':
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return _wrapped_view