from .models import HistorialEstado, SolicitudCredito
from usuarios.models import PerfilUsuario
import random
from django.db import transaction
from decimal import Decimal, ROUND_HALF_UP


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

def ejecutar_motor_recomendacion(datos_analisis):
    """
    Toma los datos ingresados por el analista y devuelve una recomendación.
    'datos_analisis' es un diccionario, como form.cleaned_data
    """
    # Usamos .get() para manejar campos que podrían no venir en el formulario
    if datos_analisis.get('tiene_procesos_judiciales'):
        return False, "Se recomienda RECHAZAR. El cliente presenta procesos judiciales."

    if datos_analisis.get('mora_telco_mayor_300k'):
        return False, "Se recomienda RECHAZAR. Presenta mora en Telco > $300.000."
    
    if datos_analisis.get('mora_otros_mayor_500k'):
        return False, "Se recomienda RECHAZAR. Presenta mora en otros productos > $500.000."
    
    huellas = datos_analisis.get('huellas_consulta', 0)
    if huellas > 3:
        return False, f"Se recomienda RECHAZAR. Excede el número de huellas de consulta ({huellas} > 3)."

    # Aquí se podrían añadir más reglas del motor de riesgo que dejamos pendientes
    
    return True, "Se recomienda APROBAR. El cliente cumple con las políticas de riesgo evaluadas."


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


def intentar_asignar_solicitud_en_espera():
    """
    Busca si hay solicitudes en la cola de espera y, si hay,
    intenta asignarla a un analista libre.
    Esta función actúa como el "gatillo" cuando un analista se libera.
    """
    # 1. Busca la solicitud más antigua que esté en espera de asignación
    solicitud_en_espera = SolicitudCredito.objects.filter(
        estado=SolicitudCredito.ESTADO_EN_ASIGNACION
    ).order_by('fecha_actualizacion').first() # .first() obtiene solo una o None

    if solicitud_en_espera:
        # 2. Si se encuentra una, llama a nuestra función de asignación existente
        print(f"Se encontró la solicitud en espera #{solicitud_en_espera.id}. Intentando asignar...")
        asignar_solicitud_a_analista(solicitud_en_espera.id)
    else:
        print("No hay solicitudes en la cola de espera.")





# Reemplaza tu función calcular_capacidad_pago_service existente con esta:
def calcular_capacidad_pago_service(solicitud: SolicitudCredito):
    """
    Calcula la capacidad de pago con la lógica de negocio final, incluyendo el
    ajuste del factor por personas a cargo.
    """
    # --- 1. PARÁMETROS Y DATOS DE ENTRADA ---
    ingresos = solicitud.ingresos_totales or Decimal('0')
    if ingresos <= 0:
        return {'Error': 'El ingreso mensual debe ser mayor a cero.'}
    
    SMLV = Decimal('1423500')
    
    # Tabla de parámetros actualizada y ampliada
    parametros = [
        {"min": SMLV, "max": SMLV * Decimal('1.5'), "Propia_1": Decimal('0.9'),  "Propia_2": Decimal('0.8'),  "NoPropia_1": Decimal('0.95'), "NoPropia_2": Decimal('0.85')},
        {"min": SMLV * Decimal('1.5'), "max": SMLV * Decimal('2.0'), "Propia_1": Decimal('0.65'), "Propia_2": Decimal('0.60'), "NoPropia_1": Decimal('0.70'), "NoPropia_2": Decimal('0.65')},
        {"min": SMLV * Decimal('2.0'), "max": SMLV * Decimal('3.0'), "Propia_1": Decimal('0.58'), "Propia_2": Decimal('0.51'), "NoPropia_1": Decimal('0.63'), "NoPropia_2": Decimal('0.56')},
        {"min": SMLV * Decimal('3.0'), "max": SMLV * Decimal('4.0'), "Propia_1": Decimal('0.51'), "Propia_2": Decimal('0.40'), "NoPropia_1": Decimal('0.56'), "NoPropia_2": Decimal('0.45')},
        {"min": SMLV * Decimal('4.0'), "max": SMLV * Decimal('6.0'), "Propia_1": Decimal('0.48'), "Propia_2": Decimal('0.38'), "NoPropia_1": Decimal('0.53'), "NoPropia_2": Decimal('0.43')},
        {"min": SMLV * Decimal('6.0'), "max": Decimal('1000000000'), "Propia_1": Decimal('0.45'), "Propia_2": Decimal('0.35'), "NoPropia_1": Decimal('0.50'), "NoPropia_2": Decimal('0.40')}
    ]

    # --- 2. LÓGICA DE CÁLCULO (Traducción 1:1 del script) ---
    
    # a. Determinar la columna a usar
    columna = f"{'Propia' if solicitud.tipo_vivienda == 'PROPIA' else 'NoPropia'}_{solicitud.num_aportantes}"

    # b. Encontrar el factor base
    factor = None
    for fila in parametros:
        if fila["min"] <= ingresos < fila["max"]:
            factor = fila[columna]
            break
    
    if factor is None:
        return {'Error': 'No se encontró un rango de parámetros para los ingresos.'}

    # c. --- ¡NUEVA LÓGICA DE AJUSTE DEL FACTOR! ---
    # Convertimos el string a int para la comparación. Manejamos el caso de '+5'.
    try:
        personas_a_cargo_num = int(solicitud.personas_a_cargo)
    except (ValueError, TypeError):
        personas_a_cargo_num = 5 # Asumimos que '+5' es >= 2

    if personas_a_cargo_num == 1:
        factor *= Decimal('1.02')
    elif personas_a_cargo_num >= 2:
        factor *= Decimal('1.05')
    
    # d. Calcular gastos estimados y compararlos con los reportados
    gastos_personales_estimados = ingresos * factor
    gastos_personales_reportados = solicitud.gastos_personales or Decimal('0')
    gastos_personales_utilizados = max(gastos_personales_estimados, gastos_personales_reportados)

    # e. Calcular capacidad de pago final
    gastos_financieros = solicitud.gastos_financieros or Decimal('0')
    capacidad_pago = ingresos - (gastos_personales_utilizados + gastos_financieros)
    
    # --- 3. DEVOLVER DICCIONARIO DE RESULTADOS ---
    def round_currency(value):
        return value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    return {
        'Ingresos Mensuales': round_currency(ingresos),
        'Gastos Personales (Reportado por cliente)': round_currency(gastos_personales_reportados),
        'Gastos Personales (Estimado y ajustado por sistema)': round_currency(gastos_personales_estimados),
        'Gasto Principal (El mayor de los dos)': round_currency(gastos_personales_utilizados),
        '(-) Gastos Financieros Reportados': round_currency(gastos_financieros),
        'Capacidad de Pago Mensual (FINAL)': round_currency(capacidad_pago),
    }



def calcular_oferta_service(solicitud: SolicitudCredito):
    """
    Toma la capacidad de pago y un plazo para calcular el monto máximo del préstamo.
    """
    TASA_INTERES_MENSUAL = Decimal('0.023')
    SEGURO_PCT = Decimal('0.0025')
    FGS_PCT = Decimal('0.0025')

    cuota_maxima = solicitud.capacidad_pago_calculada or Decimal('0')
    plazo_meses = solicitud.plazo_oferta
    
    if cuota_maxima <= 0 or not plazo_meses or plazo_meses <= 0:
        return {'Error': 'La capacidad de pago y el plazo deben ser mayores a cero.'}

    tasa_total_mensual = TASA_INTERES_MENSUAL + SEGURO_PCT + FGS_PCT
    r, n = tasa_total_mensual, plazo_meses
    
    try:
        factor = (Decimal('1') + r) ** n
        monto_maximo = cuota_maxima * (factor - Decimal('1')) / (r * factor)
    except (ZeroDivisionError, OverflowError):
        return {'Error': 'Cálculo no válido con los parámetros dados.'}
        
    def round_currency(value):
        return value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    return {
        'Monto Máximo a Prestar': round_currency(monto_maximo),
        'Cuota Mensual Estimada': round_currency(cuota_maxima),
        'Plazo': plazo_meses,
        'Tasa Total Mensual Aplicada': f"{(tasa_total_mensual * 100):.2f}%"
    }
