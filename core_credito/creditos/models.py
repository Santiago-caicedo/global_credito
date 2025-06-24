from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from datetime import date

class SolicitudCredito(models.Model):
    """
    Modelo central que representa una única solicitud de crédito y su estado
    a lo largo de todo el flujo de trabajo.
    """
    # ---- Definición de Estados del Flujo ----
    ESTADO_NUEVO = 'NUEVO'
    ESTADO_EN_EVALUACION = 'EN_EVALUACION'
    ESTADO_RECHAZADO_AUTO = 'RECHAZADO_AUTO'
    ESTADO_PEND_DOCUMENTOS = 'PEND_DOCUMENTOS'
    ESTADO_EN_ASIGNACION = 'EN_ASIGNACION'
    ESTADO_EN_ANALISIS = 'EN_ANALISIS'
    ESTADO_PREAPROBADO = 'PREAPROBADO'
    ESTADO_RECHAZADO_ANALISTA = 'RECHAZADO_ANALISTA'
    ESTADO_PEND_DOCS_ADICIONALES = 'PEND_DOCS_ADICIONALES'
    ESTADO_EN_VALIDACION_DOCS = 'EN_VALIDACION_DOCS'
    ESTADO_DOCS_CORRECCION = 'DOCS_CORRECCION'
    ESTADO_PEND_APROB_DIRECTOR = 'PEND_APROB_DIRECTOR'
    ESTADO_APROBADO = 'APROBADO'
    ESTADO_RECHAZADO_DIRECTOR = 'RECHAZADO_DIRECTOR'

    ESTADOS_CHOICES = [
        (ESTADO_NUEVO, 'Nuevo'),
        (ESTADO_EN_EVALUACION, 'En Evaluación Automática'),
        (ESTADO_RECHAZADO_AUTO, 'Rechazado Automáticamente'),
        (ESTADO_PEND_DOCUMENTOS, 'Pendiente Carga Documentos Iniciales'),
        (ESTADO_EN_ASIGNACION, 'En Espera de Asignación de Analista'),
        (ESTADO_EN_ANALISIS, 'En Análisis por Analista'),
        (ESTADO_PREAPROBADO, 'Pre-Aprobado por Analista'),
        (ESTADO_RECHAZADO_ANALISTA, 'Rechazado por Analista'),
        (ESTADO_PEND_DOCS_ADICIONALES, 'Pendiente Documentos Adicionales'),
        (ESTADO_EN_VALIDACION_DOCS, 'En Validación de Documentos'),
        (ESTADO_DOCS_CORRECCION, 'Documentos en Corrección'),
        (ESTADO_PEND_APROB_DIRECTOR, 'Pendiente Aprobación Director'),
        (ESTADO_APROBADO, 'Aprobado Final'),
        (ESTADO_RECHAZADO_DIRECTOR, 'Rechazado por Director'),
    ]

    # ---- SECCIÓN 1: Datos del Formulario Inicial del Asesor ----
    # Campos requeridos para el primer motor de decisión.
    OCUPACION_EMPLEADO = 'EMPLEADO'
    OCUPACION_INDEPENDIENTE = 'INDEPENDIENTE'
    OCUPACION_PENSIONADO = 'PENSIONADO'
    OCUPACION_CHOICES = [
        (OCUPACION_EMPLEADO, 'Empleado'),
        (OCUPACION_INDEPENDIENTE, 'Independiente'),
        (OCUPACION_PENSIONADO, 'Pensionado'),
    ]

    cedula = models.CharField("Cédula del cliente", max_length=20, unique=True)
    nombre_completo = models.CharField("Nombre completo del cliente", max_length=255)
    # NOTA: Los campos de fecha y ocupación se mantienen `nullable` para no romper la BD existente,
    # pero serán requeridos a nivel del formulario.
    fecha_nacimiento = models.DateField("Fecha de nacimiento", null=True, blank=True)
    fecha_expedicion = models.DateField("Fecha de expedición de la cédula", null=True, blank=True)
    ocupacion = models.CharField("Ocupación", max_length=20, choices=OCUPACION_CHOICES, null=True, blank=True)
    ingresos_totales = models.DecimalField("Ingresos Totales (COP)", max_digits=12, decimal_places=2, null=True, blank=True)


    # ---- SECCIÓN 2: Datos de Enriquecimiento y Análisis (Para Fases Posteriores) ----
    # Campos que serán llenados y usados después del primer filtro.
    PERSONAS_CARGO_0 = '0'
    PERSONAS_CARGO_1 = '1'
    PERSONAS_CARGO_2 = '2'
    PERSONAS_CARGO_3 = '3'
    PERSONAS_CARGO_4 = '4'
    PERSONAS_CARGO_MAS_5 = '+5'
    PERSONAS_CARGO_CHOICES = [
        (PERSONAS_CARGO_0, '0'),
        (PERSONAS_CARGO_1, '1'),
        (PERSONAS_CARGO_2, '2'),
        (PERSONAS_CARGO_3, '3'),
        (PERSONAS_CARGO_4, '4'),
        (PERSONAS_CARGO_MAS_5, 'Más de 5'),
    ]
    
    tiene_vivienda_propia = models.BooleanField("¿Tiene vivienda propia?", default=False)
    personas_a_cargo = models.CharField("Personas a cargo", max_length=10, choices=PERSONAS_CARGO_CHOICES, null=True, blank=True)
    
    # Datos de centrales de riesgo
    mora_telco_mayor_300k = models.BooleanField("¿Mora Telco > $300.000?", null=True)
    mora_otros_mayor_500k = models.BooleanField("¿Mora otros productos > $500.000?", null=True)
    es_tipo_0 = models.BooleanField("¿Es tipo 0?", null=True)
    huellas_consulta = models.PositiveIntegerField("Número de huellas de consulta", null=True, blank=True)
    tiene_procesos_judiciales = models.BooleanField("¿Tiene procesos judiciales?", null=True)
    causal_no_sujeto = models.CharField("Causal de no sujeto a crédito", max_length=100, null=True, blank=True)
    actividad_economica_restringida = models.CharField("Actividad Económica (si es restringida)", max_length=100, null=True, blank=True)

    # ---- Campos de Control del Sistema ----
    asesor_comercial = models.ForeignKey(User, on_delete=models.PROTECT, related_name='solicitudes_creadas')
    analista_asignado = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='solicitudes_asignadas')
    estado = models.CharField(max_length=30, choices=ESTADOS_CHOICES, default=ESTADO_NUEVO)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    # ---- Campos de Análisis (llenados por el Analista) ----
    observacion_centrales_riesgo = models.TextField("Observación Centrales de Riesgo", blank=True, null=True)
    observacion_llamada_cliente = models.TextField("Observación Llamada con Cliente", blank=True, null=True)
    observacion_referencias = models.TextField("Observación de Referencias", blank=True, null=True)

    class Meta:
        verbose_name = "Solicitud de Crédito"
        verbose_name_plural = "Solicitudes de Crédito"
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"Solicitud #{self.id} - {self.nombre_completo} ({self.get_estado_display()})"

    @property
    def edad(self):
        today = date.today()
        if not self.fecha_nacimiento:
            return None
        return today.year - self.fecha_nacimiento.year - ((today.month, today.day) < (self.fecha_nacimiento.month, self.fecha_nacimiento.day))
    
    def get_estado_color_class(self):
        """
        Retorna la clase de CSS de Bootstrap para el color del badge
        según el estado actual de la solicitud.
        """
        # Rechazados en Rojo
        if 'RECHAZADO' in self.estado:
            return 'bg-danger'

        # Aprobados/Listos en Verde
        elif self.estado == self.ESTADO_PEND_DOCUMENTOS or 'APROBADO' in self.estado:
            return 'bg-success'

        # Estados de espera de acción del usuario en Amarillo
        elif 'PEND' in self.estado or 'CORRECCION' in self.estado:
            return 'bg-warning text-dark'
            
        # --- NUEVA LÓGICA AQUÍ ---
        # En espera de asignación en Celeste
        elif self.estado == self.ESTADO_EN_ASIGNACION:
            return 'bg-info text-dark'
            
        # En proceso activo en Azul
        elif 'EN_' in self.estado: # Ahora solo capturará 'EN_ANALISIS', etc.
            return 'bg-primary'

        # Estado por defecto en Gris
        return 'bg-secondary'


class Referencia(models.Model):
    """ Almacena las referencias (personales/familiares) de una solicitud. """
    TIPO_PERSONAL = 'PERSONAL'
    TIPO_FAMILIAR = 'FAMILIAR'
    TIPOS_CHOICES = [
        (TIPO_PERSONAL, 'Personal'),
        (TIPO_FAMILIAR, 'Familiar'),
    ]
    solicitud = models.ForeignKey(SolicitudCredito, on_delete=models.CASCADE, related_name='referencias')
    nombre_completo = models.CharField(max_length=255)
    numero_contacto = models.CharField(max_length=20)
    parentesco = models.CharField(max_length=50, help_text="Ej: Amigo, Primo, Padre, etc.")
    tipo = models.CharField(max_length=10, choices=TIPOS_CHOICES)

    class Meta:
        verbose_name = "Referencia"
        verbose_name_plural = "Referencias"

    def __str__(self):
        return f"{self.get_tipo_display()}: {self.nombre_completo} para Solicitud #{self.solicitud.id}"

class HistorialEstado(models.Model):
    """ Modela una bitácora o log de todos los cambios de estado de una solicitud. """
    solicitud = models.ForeignKey(SolicitudCredito, on_delete=models.CASCADE, related_name='historial')
    estado_anterior = models.CharField(max_length=30, null=True, blank=True)
    estado_nuevo = models.CharField(max_length=30)
    fecha_cambio = models.DateTimeField(auto_now_add=True)
    usuario_responsable = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    observaciones = models.TextField(blank=True, null=True, help_text="Razón del cambio de estado, si aplica.")

    class Meta:
        verbose_name = "Historial de Estado"
        verbose_name_plural = "Historiales de Estado"
        ordering = ['-fecha_cambio']

    def __str__(self):
        return f"Solicitud #{self.solicitud.id}: {self.estado_anterior} -> {self.estado_nuevo}"

class Documento(models.Model):
    """ Almacena los archivos asociados a una solicitud de crédito. """
    # --- Definición de Choices para el Modelo ---
    DOCUMENTOS_CHOICES = [
        ('CEDULA', 'Cédula'),
        ('DECLARACION_RENTA', 'Declaración de Renta'),
        ('CERTIFICADO_LABORAL', 'Certificado Laboral'),
        ('AUTORIZACION_CONSULTA', 'Autorización de Consulta a Centrales'),
    ]

    solicitud = models.ForeignKey(SolicitudCredito, on_delete=models.CASCADE, related_name='documentos')
    # --- Campo Actualizado con `choices` ---
    nombre_documento = models.CharField(
        max_length=100,
        choices=DOCUMENTOS_CHOICES,
        help_text="Ej: Cédula, Certificado Laboral"
    )
    archivo = models.FileField(upload_to='documentos/%Y/%m/%d/')
    fecha_carga = models.DateTimeField(auto_now_add=True)
    ok_analista = models.BooleanField("Documento Validado (OK)", default=False)
    observacion_correccion = models.TextField("Observación para Corrección", blank=True, null=True)

    class Meta:
        verbose_name = "Documento"
        verbose_name_plural = "Documentos"

    def __str__(self):
        # Ahora podemos usar el método get_..._display() aquí también!
        return f"{self.get_nombre_documento_display()} de Solicitud #{self.solicitud.id}"