# usuarios/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import PerfilUsuario


class PerfilUsuarioInline(admin.StackedInline):
    """Inline para mostrar/editar el perfil dentro del admin de User"""
    model = PerfilUsuario
    can_delete = False
    verbose_name = 'Perfil'
    verbose_name_plural = 'Perfil de Usuario'
    fields = ('rol', 'telefono', 'solicitud_actual')
    readonly_fields = ('solicitud_actual',)  # Solo lectura, se asigna automaticamente


class UserAdmin(BaseUserAdmin):
    """Admin personalizado de User que incluye el perfil inline"""
    inlines = (PerfilUsuarioInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'get_rol', 'is_active', 'is_staff')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'perfil__rol')
    search_fields = ('username', 'first_name', 'last_name', 'email')

    def get_rol(self, obj):
        """Muestra el rol del usuario en la lista"""
        if hasattr(obj, 'perfil'):
            return obj.perfil.get_rol_display()
        return '-'
    get_rol.short_description = 'Rol'
    get_rol.admin_order_field = 'perfil__rol'


# Desregistrar el admin por defecto de User y registrar el personalizado
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(PerfilUsuario)
class PerfilUsuarioAdmin(admin.ModelAdmin):
    """Admin para gestionar perfiles directamente"""
    list_display = ('usuario', 'rol', 'telefono', 'solicitud_actual')
    list_filter = ('rol',)
    search_fields = ('usuario__username', 'usuario__email', 'usuario__first_name', 'usuario__last_name')
    raw_id_fields = ('usuario', 'solicitud_actual')

    fieldsets = (
        ('Usuario', {
            'fields': ('usuario',)
        }),
        ('Rol y Contacto', {
            'fields': ('rol', 'telefono')
        }),
        ('Asignacion Actual (Analistas)', {
            'fields': ('solicitud_actual',),
            'classes': ('collapse',),
            'description': 'Solo aplica para analistas. Se asigna automaticamente.'
        }),
    )
