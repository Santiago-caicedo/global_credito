from .models import HistorialEstado, SolicitudCredito
from usuarios.models import PerfilUsuario
import random
from django.db import transaction

# --- MOTOR INICIAL (FASE 1) ---
def ejecutar_motor_inicial(solicitud: SolicitudCredito):
    """
    Ejecuta el primer filtro automático con los datos de entrada del asesor.
    Retorna el nuevo estado y una observación.
    """
    edad = solicitud.edad
    
    # 1. Validación de edad
    if not (18 <= edad <= 65):
        return SolicitudCredito.ESTADO_RECHAZADO_AUTO, "Rechazado por política de edad (18-65 años)."

    # 2. Validación de ingresos por ocupación
    if solicitud.ocupacion == SolicitudCredito.OCUPACION_EMPLEADO and solicitud.ingresos_totales < 2000000:
        return SolicitudCredito.ESTADO_RECHAZADO_AUTO, "Rechazado por ingresos insuficientes para empleado (< $2.000.000)."
    
    if solicitud.ocupacion == SolicitudCredito.OCUPACION_INDEPENDIENTE and solicitud.ingresos_totales < 3000000:
        return SolicitudCredito.ESTADO_RECHAZADO_AUTO, "Rechazado por ingresos insuficientes para independiente (< $3.000.000)."

    # Si pasa todos los filtros iniciales, avanza para ser asignado a un analista.
    return SolicitudCredito.ESTADO_PEND_DOCUMENTOS, "Pasa primer filtro. Pendiente de carga de documentos."


# --- LÓGICA PARA FASES POSTERIORES (LA GUARDAMOS PARA EL FUTURO) ---

def enriquecer_datos_con_centrales(solicitud: SolicitudCredito):
    """
    Simula la obtención de datos de fuentes externas (centrales de riesgo, etc.)
    ESTA FUNCIÓN SE LLAMARÁ MÁS ADELANTE EN EL FLUJO.
    """
    # TODO: Implementar llamadas reales a servicios externos.
    solicitud.mora_telco_mayor_300k = False
    solicitud.mora_otros_mayor_500k = False
    solicitud.es_tipo_0 = False
    solicitud.huellas_consulta = 2
    solicitud.tiene_procesos_judiciales = False
    solicitud.causal_no_sujeto = None
    solicitud.actividad_economica_restringida = None
    solicitud.save()
    return solicitud

def ejecutar_motor_preseleccion_analista(solicitud: SolicitudCredito):
    """
    Ejecuta el segundo filtro automático con los datos de las centrales de riesgo.
    Esta lógica es la que teníamos antes, ahora separada.
    """
    # Aquí iría el resto de las validaciones: moras, huellas, listas restrictivas, etc.
    # Por ahora, simplemente la definimos pero no la usamos.
    print("Ejecutando motor de preselección del analista (lógica futura)...")
    return True, "Análisis de riesgo superado (lógica futura)."


@transaction.atomic # Asegura que todas las operaciones de BD se hagan juntas o ninguna
def asignar_solicitud_a_analista(solicitud_id):
    """
    Intenta asignar una solicitud específica a un analista libre.
    """
    try:
        solicitud = SolicitudCredito.objects.get(id=solicitud_id, estado=SolicitudCredito.ESTADO_EN_ASIGNACION)
    except SolicitudCredito.DoesNotExist:
        return # La solicitud no existe o no está en el estado correcto

    # 1. Encontrar todos los perfiles de analistas que están libres
    analistas_libres = PerfilUsuario.objects.filter(
        rol=PerfilUsuario.ROL_ANALISTA,
        solicitud_actual__isnull=True
    )

    if not analistas_libres.exists():
        # No hay analistas libres, la solicitud permanece en la cola
        print(f"No hay analistas libres. Solicitud #{solicitud.id} queda en espera.")
        return

    # 2. Si hay analistas libres, elegir uno al azar
    analista_elegido_perfil = random.choice(list(analistas_libres))
    
    # 3. Realizar la asignación
    # Ocupar al analista
    analista_elegido_perfil.solicitud_actual = solicitud
    analista_elegido_perfil.save()
    
    # Asignar la solicitud y cambiar su estado
    solicitud.analista_asignado = analista_elegido_perfil.usuario
    solicitud.estado = SolicitudCredito.ESTADO_EN_ANALISIS
    solicitud.save()

    print(f"¡Éxito! Solicitud #{solicitud.id} asignada a {analista_elegido_perfil.usuario.username}.")

    # 4. Registrar en el historial
    HistorialEstado.objects.create(
        solicitud=solicitud,
        estado_anterior=SolicitudCredito.ESTADO_EN_ASIGNACION,
        estado_nuevo=SolicitudCredito.ESTADO_EN_ANALISIS,
        observaciones=f"Asignado automáticamente al analista {analista_elegido_perfil.usuario.username}."
    )
