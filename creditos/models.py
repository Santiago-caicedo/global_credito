import os
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from datetime import date

from django.forms import ValidationError

class SolicitudCredito(models.Model):
    """
    Modelo central que representa una única solicitud de crédito y su estado
    a lo largo de todo el flujo de trabajo.
    """
    # ---- 1. DEFINICIÓN DE ESTADOS Y CHOICES (Organizados) ----
    
    # --- Estados del Flujo ---
    ESTADO_NUEVO = 'NUEVO'
    ESTADO_RECHAZADO_AUTO = 'RECHAZADO_AUTO'
    ESTADO_PEND_DOCUMENTOS = 'PEND_DOCUMENTOS'
    ESTADO_EN_ASIGNACION = 'EN_ASIGNACION'
    ESTADO_EN_ANALISIS = 'EN_ANALISIS'
    ESTADO_PREAPROBADO = 'PREAPROBADO'
    ESTADO_RECHAZADO_ANALISTA = 'RECHAZADO_ANALISTA'
    ESTADO_DOCS_FINALES_CORRECCION = 'DOCS_FINALES_CORRECCION'  
    ESTADO_PEND_DOCS_ADICIONALES = 'PEND_DOCS_ADICIONALES'
    ESTADO_EN_VALIDACION_DOCS = 'EN_VALIDACION_DOCS'
    ESTADO_DOCS_CORRECCION = 'DOCS_CORRECCION'
    ESTADO_PEND_APROB_DIRECTOR = 'PEND_APROB_DIRECTOR'
    ESTADO_APROBADO = 'APROBADO'
    ESTADO_RECHAZADO_DIRECTOR = 'RECHAZADO_DIRECTOR'
    ESTADO_DESEMBOLSADO = 'DESEMBOLSADO'

    ESTADOS_CHOICES = [
        (ESTADO_NUEVO, 'Nuevo'),
        (ESTADO_RECHAZADO_AUTO, 'Rechazado Automáticamente'),
        (ESTADO_PEND_DOCUMENTOS, 'Pendiente Carga Documentos Iniciales'),
        (ESTADO_EN_ASIGNACION, 'En Espera de Asignación de Analista'),
        (ESTADO_EN_ANALISIS, 'En Análisis por Analista'),
        (ESTADO_PREAPROBADO, 'Pre-Aprobado por Analista'),
        (ESTADO_RECHAZADO_ANALISTA, 'Rechazado por Analista'),
        (ESTADO_DOCS_FINALES_CORRECCION, 'En Corrección de Documentos Finales'),
        (ESTADO_PEND_DOCS_ADICIONALES, 'Pendiente Documentos Adicionales'),
        (ESTADO_EN_VALIDACION_DOCS, 'En Validación de Documentos'),
        (ESTADO_DOCS_CORRECCION, 'Documentos en Corrección'),
        (ESTADO_PEND_APROB_DIRECTOR, 'Pendiente Aprobación Director'),
        (ESTADO_APROBADO, 'Aprobado Final'),
        (ESTADO_RECHAZADO_DIRECTOR, 'Rechazado por Director'),
        (ESTADO_DESEMBOLSADO, 'Desembolsado'),
    ]

    # --- Choices para campos de formulario ---
    # --- Choices para Ocupación (¡CORRECCIÓN!) ---
    OCUPACION_EMPLEADO = 'EMPLEADO'
    OCUPACION_INDEPENDIENTE = 'INDEPENDIENTE'
    OCUPACION_PENSIONADO = 'PENSIONADO'
    OCUPACION_CHOICES = [
        (OCUPACION_EMPLEADO, 'Empleado'),
        (OCUPACION_INDEPENDIENTE, 'Independiente'),
        (OCUPACION_PENSIONADO, 'Pensionado'),
    ]
    VIVIENDA_CHOICES = [('PROPIA', 'Propia'), ('FAMILIAR', 'Familiar'), ('ARRIENDO', 'En Arriendo')]
    ESTADO_CIVIL_CHOICES = [('SOLTERO', 'Soltero/a'), ('CASADO', 'Casado/a'), ('DIVORCIADO', 'Divorciado/a'), ('UNION_LIBRE', 'Unión Libre')]
    SEXO_CHOICES = [('HOMBRE', 'Hombre'), ('MUJER', 'Mujer')]
    PERSONAS_CARGO_CHOICES = [('0', '0'), ('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('+5', 'Más de 5')]
    NUM_APORTANTES_CHOICES = [(1, '1'), (2, '2')]


    # ---- 2. CAMPOS DEL FORMULARIO INICIAL DEL ASPIRANTE (OBLIGATORIOS) ----
    cedula = models.CharField("Numero de Cedula", max_length=20, unique=True)
    nombre_completo = models.CharField("Nombre Completo", max_length=255)
    fecha_nacimiento = models.DateField("Fecha de Nacimiento")
    fecha_expedicion = models.DateField("Fecha de Expedicion de la Cedula")
    ocupacion = models.CharField("Ocupacion", max_length=20, choices=OCUPACION_CHOICES)
    ingresos_totales = models.DecimalField("Ingresos Mensuales", max_digits=12, decimal_places=2)
    monto_solicitado = models.DecimalField(
        "Monto Solicitado",
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(500000, "El monto solicitado debe ser de al menos $500,000.")]
    )
    plazo_solicitado = models.PositiveSmallIntegerField(
        "Plazo Solicitado (meses)",
        validators=[MinValueValidator(6, "El plazo minimo es de 6 meses.")]
    )
    convenio = models.CharField(
        "Convenio",
        max_length=100,
        blank=True,
        null=True,
        help_text="Convenio o alianza comercial asociada a esta solicitud"
    )

    # ---- 3. CAMPOS DE ANÁLISIS DEL ANALISTA (OPCIONALES a nivel de BD, obligatorios en su propio formulario) ----
    tipo_vivienda = models.CharField("Tipo de Vivienda", max_length=20, choices=VIVIENDA_CHOICES, null=True, blank=True)
    personas_a_cargo = models.CharField("Personas a cargo", max_length=10, choices=PERSONAS_CARGO_CHOICES, null=True, blank=True)
    gastos_personales = models.DecimalField("Gastos Personales Reportados", max_digits=12, decimal_places=2, null=True, blank=True)
    gastos_financieros = models.DecimalField("Gastos Financieros Confirmados", max_digits=12, decimal_places=2, null=True, blank=True)
    otros_gastos = models.DecimalField("Otros Gastos Mensuales", max_digits=12, decimal_places=2, null=True, blank=True)
    direccion_residencia = models.CharField("Dirección de Residencia", max_length=255, null=True, blank=True)
    ciudad_residencia = models.CharField("Ciudad de Residencia", max_length=100, null=True, blank=True)
    departamento_residencia = models.CharField("Departamento de Residencia", max_length=100, null=True, blank=True)
    barrio_residencia = models.CharField("Barrio de Residencia", max_length=100, null=True, blank=True)
    estrato = models.PositiveSmallIntegerField("Estrato", null=True, blank=True)
    estado_civil = models.CharField("Estado Civil", max_length=20, choices=ESTADO_CIVIL_CHOICES, null=True, blank=True)
    sexo = models.CharField("Sexo", max_length=10, choices=SEXO_CHOICES, null=True, blank=True)
    num_aportantes = models.PositiveSmallIntegerField("Número de Aportantes", default=1, choices=NUM_APORTANTES_CHOICES, null=True, blank=True)
    mora_telco_mayor_300k = models.BooleanField("¿Mora Telco > $300.000?", null=True)
    mora_otros_mayor_500k = models.BooleanField("¿Mora otros productos > $500.000?", null=True)
    es_tipo_0 = models.BooleanField("¿Es tipo 0?", null=True)
    huellas_consulta = models.PositiveIntegerField("Número de huellas de consulta", default=0, null=True, blank=True)
    tiene_procesos_judiciales = models.BooleanField("¿Tiene procesos judiciales?", null=True)
    observacion_referencias = models.TextField("Observación de Referencias", blank=True, null=True)

    # ---- 4. CAMPOS DEL ASPIRANTE (NUEVO FLUJO PUBLICO) ----
    email_aspirante = models.EmailField("Email del Aspirante", max_length=255, default='')
    telefono_aspirante = models.CharField("Telefono del Aspirante", max_length=20, default='')
    aspirante = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='solicitudes_como_aspirante',
        null=True,
        blank=True,
        help_text="Usuario vinculado después de registro"
    )
    token_registro = models.CharField(
        "Token de Registro",
        max_length=64,
        null=True,
        blank=True,
        unique=True,
        help_text="Token temporal para completar registro post-aprobación"
    )
    token_expiracion = models.DateTimeField("Expiración del Token", null=True, blank=True)

    # ---- 5. CAMPOS DE CONTROL Y RESULTADOS ----
    analista_asignado = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='solicitudes_asignadas')
    estado = models.CharField(max_length=30, choices=ESTADOS_CHOICES, default=ESTADO_NUEVO)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    observacion_analisis_documentos = models.TextField("Observación del Análisis de Documentos", blank=True, null=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    recomendacion_sistema_aprobada = models.BooleanField("¿Sistema recomienda aprobar?", null=True)
    recomendacion_sistema_texto = models.TextField("Texto de recomendación del sistema", blank=True, null=True)
    observacion_oferta_final = models.TextField("Justificación de la Oferta Definitiva", blank=True, null=True)
    capacidad_pago_calculada = models.DecimalField("Capacidad de Pago Calculada", max_digits=12, decimal_places=2, null=True, blank=True)
    plazo_oferta = models.PositiveSmallIntegerField("Plazo de la Oferta (meses)", null=True, blank=True)
    monto_aprobado_calculado = models.DecimalField("Monto Máximo Aprobado", max_digits=12, decimal_places=2, null=True, blank=True)

    #acá para el cambio
    class Meta:
        verbose_name = "Solicitud de Crédito"
        verbose_name_plural = "Solicitudes de Crédito"
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"Solicitud #{self.id} - {self.nombre_completo} ({self.get_estado_display()})"

    @property
    def edad(self):
        if not self.fecha_nacimiento: return None
        today = date.today()
        return today.year - self.fecha_nacimiento.year - ((today.month, today.day) < (self.fecha_nacimiento.month, self.fecha_nacimiento.day))

    def get_estado_color_class(self):
        if self.estado == self.ESTADO_DESEMBOLSADO: return 'bg-success'
        if 'RECHAZADO' in self.estado: return 'bg-danger'
        if self.estado == self.ESTADO_PEND_DOCUMENTOS or 'APROBADO' in self.estado: return 'bg-success'
        if self.estado == self.ESTADO_EN_ASIGNACION: return 'bg-info text-dark'
        if 'PEND' in self.estado or 'CORRECCION' in self.estado: return 'bg-warning text-dark'
        if 'EN_' in self.estado: return 'bg-primary'
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
    

def validate_file_extension_and_size(value):
    """
    Validador personalizado para archivos. Comprueba la extensión y el tamaño.
    """
    # 1. Obtenemos la extensión del archivo y la pasamos a minúsculas
    ext = os.path.splitext(value.name)[1].lower()
    
    # 2. Definimos las extensiones permitidas
    valid_extensions = ['.pdf', '.jpg', '.jpeg', '.png']
    if not ext in valid_extensions:
        raise ValidationError('Tipo de archivo no permitido. Solo se aceptan PDF, JPG y PNG.')
        
    # 3. Definimos el tamaño máximo en bytes (5 MB)
    max_size = 5 * 1024 * 1024 # 5 Megabytes
    if value.size > max_size:
        raise ValidationError('El archivo es demasiado grande. El tamaño máximo permitido es de 5 MB.')

class Documento(models.Model):
    """ Almacena los archivos asociados a una solicitud de crédito. """
    # Documentos del Aspirante (Fase 1)
    TIPO_CEDULA = 'CEDULA'
    TIPO_RENTA = 'DECLARACION_RENTA'
    TIPO_LABORAL = 'CERTIFICADO_LABORAL'
    TIPO_AUTORIZACION = 'AUTORIZACION_CONSULTA'
    
    # Documentos del Analista (Fase 3)
    TIPO_HISTORIAL_CREDITO = 'HISTORIAL_CREDITO'
    TIPO_PROCESOS_JUDICIALES = 'PROCESOS_JUDICIALES'
    TIPO_ADRESS = 'ADRESS'
    TIPO_CONTRALORIA = 'CONTRALORIA'
    TIPO_PROCURADURIA = 'PROCURADURIA'
    TIPO_OTRAS_CONSULTAS = 'OTRAS_CONSULTAS'

    DOCUMENTOS_CHOICES = [
        ('Documentos del Aspirante', (
            (TIPO_CEDULA, 'Cédula'),
            (TIPO_RENTA, 'Declaración de Renta'),
            (TIPO_LABORAL, 'Certificado Laboral'),
            (TIPO_AUTORIZACION, 'Autorización de Consulta a Centrales'),
        )),
        ('Documentos de Análisis', (
            (TIPO_HISTORIAL_CREDITO, 'Historial de Crédito (PDF)'),
            (TIPO_PROCESOS_JUDICIALES, 'Pantallazo de Procesos Judiciales'),
            (TIPO_ADRESS, 'Pantallazo ADRESS'),
            (TIPO_CONTRALORIA, 'Antecedentes en Contraloría (PDF)'),
            (TIPO_PROCURADURIA, 'Antecedentes en Procuraduría (Pantallazo)'),
            (TIPO_OTRAS_CONSULTAS, 'Otras Consultas (Puesto de Votación, Sisbén)'),
        )),
        ('Documentos de Cierre', (
            ('PAGARE', 'Pagaré'),
            ('CARTA_INSTRUCCIONES', 'Carta de Instrucciones'),
            ('POLIZA_SEGURO', 'Póliza de Seguro'),
            ('FORMATO_VINCULACION', 'Formato de Vinculación'),
        )),
    ]

    solicitud = models.ForeignKey(SolicitudCredito, on_delete=models.CASCADE, related_name='documentos')
    nombre_documento = models.CharField(max_length=100, choices=DOCUMENTOS_CHOICES)
    archivo = models.FileField(
        upload_to='documentos/%Y/%m/%d/',
        validators=[validate_file_extension_and_size] # Aplicamos nuestro guardián
    )
    # Nuevo campo para saber quién subió el documento
    subido_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='documentos_subidos')
    fecha_carga = models.DateTimeField(auto_now_add=True)
    ok_analista = models.BooleanField("Documento Validado (OK)", default=True)
    observacion_correccion = models.TextField("Observación para Corrección", blank=True, null=True)

    class Meta:
        verbose_name = "Documento"
        verbose_name_plural = "Documentos"

    def __str__(self):
        return f"{self.get_nombre_documento_display()} de Solicitud #{self.solicitud.id}"
    
    @property
    def extension(self):
        # Devuelve la extensión del archivo en mayúsculas (ej: 'PDF', 'PNG')
        import os
        name, extension = os.path.splitext(self.archivo.name)
        return extension.replace('.', '').upper()
    




class ParametrosGlobales(models.Model):
    """
    Un modelo Singleton para almacenar los parámetros globales del sistema
    que el Director puede modificar. Solo puede existir una instancia de este modelo.
    """
    smlv = models.DecimalField("Salario Mínimo Legal Vigente (SMLV)", max_digits=10, decimal_places=2, default=1300000)
    tasa_interes_mensual = models.DecimalField(
        "Tasa de Interés Mensual (Ej: 0.023 para 2.3%)",
        max_digits=5,
        decimal_places=4,
        default=0.0230
    )
    porcentaje_seguro = models.DecimalField(
        "Porcentaje del Seguro sobre el Monto",
        max_digits=5,
        decimal_places=4,
        default=0.0025
    )
    porcentaje_fgs = models.DecimalField(
        "Porcentaje del Fondo de Garantías (FGS)",
        max_digits=5,
        decimal_places=4,
        default=0.0025
    )

    class Meta:
        verbose_name = "Parámetro Global"
        verbose_name_plural = "Parámetros Globales"

    def __str__(self):
        return "Configuración Global del Sistema"

    def save(self, *args, **kwargs):
        # Asegura que solo exista una instancia de este modelo (patrón Singleton)
        if not self.pk and ParametrosGlobales.objects.exists():
            # Si estamos creando un nuevo objeto y ya existe uno, no lo permitimos.
            raise ValidationError('Solo puede existir una instancia de Parámetros Globales.')
        return super(ParametrosGlobales, self).save(*args, **kwargs)


class ConsultaDataCredito(models.Model):
    """
    Modelo para almacenar los resultados de consultas a DataCrédito.
    Guarda tanto la respuesta HPN (Historia + Score + Quanto) como Reconocer.
    """
    ESTADO_EXITO = 'EXITO'
    ESTADO_ERROR = 'ERROR'
    ESTADO_SIN_DATOS = 'SIN_DATOS'
    ESTADO_NO_ENCONTRADO = 'NO_ENCONTRADO'

    ESTADOS_CHOICES = [
        (ESTADO_EXITO, 'Consulta exitosa'),
        (ESTADO_ERROR, 'Error en consulta'),
        (ESTADO_SIN_DATOS, 'Sin datos en central'),
        (ESTADO_NO_ENCONTRADO, 'Identificación no encontrada'),
    ]

    solicitud = models.ForeignKey(
        SolicitudCredito,
        on_delete=models.CASCADE,
        related_name='consultas_datacredito'
    )

    # Datos de la consulta
    fecha_consulta = models.DateTimeField(auto_now_add=True)
    tipo_consulta = models.CharField(
        "Tipo de Consulta",
        max_length=20,
        choices=[('HPN', 'Historia de Crédito'), ('RECONOCER', 'Reconocer Master')],
    )
    estado_consulta = models.CharField(
        "Estado",
        max_length=20,
        choices=ESTADOS_CHOICES,
        default=ESTADO_EXITO
    )
    codigo_respuesta = models.CharField("Código de Respuesta", max_length=30, blank=True, null=True)
    mensaje_respuesta = models.TextField("Mensaje de Respuesta", blank=True, null=True)

    # --- Datos HPN (Historia de Crédito) ---
    # Score
    advance_score = models.IntegerField("Advance Score (Z0)", null=True, blank=True)
    score_descripcion = models.CharField("Descripción Score", max_length=100, blank=True, null=True)

    # Quanto (Patrimonio)
    quanto_valor = models.DecimalField("Valor Quanto (O4)", max_digits=15, decimal_places=2, null=True, blank=True)

    # Resumen de cartera
    total_obligaciones = models.IntegerField("Total Obligaciones", null=True, blank=True)
    obligaciones_al_dia = models.IntegerField("Obligaciones al Día", null=True, blank=True)
    obligaciones_mora = models.IntegerField("Obligaciones en Mora", null=True, blank=True)
    saldo_total = models.DecimalField("Saldo Total", max_digits=15, decimal_places=2, null=True, blank=True)
    saldo_mora = models.DecimalField("Saldo en Mora", max_digits=15, decimal_places=2, null=True, blank=True)
    cuota_mensual_total = models.DecimalField("Cuota Mensual Total", max_digits=15, decimal_places=2, null=True, blank=True)

    # Moras específicas
    mora_telco = models.DecimalField("Mora Telco", max_digits=12, decimal_places=2, null=True, blank=True)
    mora_sector_real = models.DecimalField("Mora Sector Real", max_digits=12, decimal_places=2, null=True, blank=True)
    mora_sector_financiero = models.DecimalField("Mora Sector Financiero", max_digits=12, decimal_places=2, null=True, blank=True)

    # Huellas de consulta (últimos 6 meses)
    huellas_ultimos_6_meses = models.IntegerField("Huellas últimos 6 meses", null=True, blank=True)

    # Vector de comportamiento (últimos 24 meses como JSON)
    vector_comportamiento = models.JSONField("Vector de Comportamiento (24m)", null=True, blank=True)

    # --- Datos Reconocer Master ---
    reconocer_ciudad = models.CharField("Ciudad (Reconocer)", max_length=100, blank=True, null=True)
    reconocer_departamento = models.CharField("Departamento (Reconocer)", max_length=100, blank=True, null=True)
    reconocer_direccion = models.CharField("Dirección (Reconocer)", max_length=255, blank=True, null=True)
    reconocer_estrato = models.CharField("Estrato (Reconocer)", max_length=10, blank=True, null=True)
    reconocer_telefono = models.CharField("Teléfono (Reconocer)", max_length=50, blank=True, null=True)
    reconocer_celular = models.CharField("Celular (Reconocer)", max_length=50, blank=True, null=True)
    reconocer_email = models.EmailField("Email (Reconocer)", blank=True, null=True)

    # Respuesta cruda (para debug y auditoría)
    respuesta_cruda = models.JSONField("Respuesta JSON Completa", null=True, blank=True)

    class Meta:
        verbose_name = "Consulta DataCrédito"
        verbose_name_plural = "Consultas DataCrédito"
        ordering = ['-fecha_consulta']

    def __str__(self):
        return f"{self.tipo_consulta} - Solicitud #{self.solicitud.id} ({self.get_estado_consulta_display()})"


class NotificacionEmail(models.Model):
    """
    Modelo para trackear las notificaciones por email enviadas a los aspirantes.
    Permite auditar y reintentar envíos fallidos.
    """
    TIPO_PREAPROBACION = 'PREAPROBACION'
    TIPO_BIENVENIDA = 'BIENVENIDA'
    TIPO_EN_ESPERA = 'EN_ESPERA'
    TIPO_ASIGNADO = 'ASIGNADO'
    TIPO_CAMBIO_ESTADO = 'CAMBIO_ESTADO'
    TIPO_DOCUMENTOS_RECHAZADOS = 'DOCS_RECHAZADOS'
    TIPO_APROBACION_FINAL = 'APROBACION_FINAL'
    TIPO_RECHAZO = 'RECHAZO'
    TIPO_RECHAZO_MOTOR = 'RECHAZO_MOTOR'

    TIPOS_CHOICES = [
        (TIPO_PREAPROBACION, 'Pre-aprobacion Inicial'),
        (TIPO_BIENVENIDA, 'Bienvenida'),
        (TIPO_EN_ESPERA, 'Solicitud en Espera'),
        (TIPO_ASIGNADO, 'Asignado a Analista'),
        (TIPO_CAMBIO_ESTADO, 'Cambio de Estado'),
        (TIPO_DOCUMENTOS_RECHAZADOS, 'Documentos Rechazados'),
        (TIPO_APROBACION_FINAL, 'Aprobación Final'),
        (TIPO_RECHAZO, 'Rechazo por Director'),
        (TIPO_RECHAZO_MOTOR, 'Rechazo Automatico'),
    ]

    solicitud = models.ForeignKey(
        SolicitudCredito,
        on_delete=models.CASCADE,
        related_name='notificaciones_email'
    )
    tipo = models.CharField("Tipo de Notificación", max_length=30, choices=TIPOS_CHOICES)
    email_destino = models.EmailField("Email de Destino")
    asunto = models.CharField("Asunto", max_length=255)
    contenido = models.TextField("Contenido del Email", blank=True, null=True)
    enviado = models.BooleanField("¿Enviado?", default=False)
    fecha_envio = models.DateTimeField("Fecha de Envío", null=True, blank=True)
    error_mensaje = models.TextField("Mensaje de Error", blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Notificación de Email"
        verbose_name_plural = "Notificaciones de Email"
        ordering = ['-fecha_creacion']

    def __str__(self):
        estado = "Enviado" if self.enviado else "Pendiente"
        return f"{self.get_tipo_display()} - Solicitud #{self.solicitud.id} ({estado})"