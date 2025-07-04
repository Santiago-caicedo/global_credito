from django import forms
from .models import ParametrosGlobales, SolicitudCredito, Documento, Referencia
from django.contrib.auth.models import User


# --- FORMULARIO 1: Para la creación inicial de la solicitud (Asesor) ---
class SolicitudCreditoForm(forms.ModelForm):
    class Meta:
        model = SolicitudCredito
        fields = [
            'cedula', 'nombre_completo', 'fecha_nacimiento', 'fecha_expedicion',
            'ocupacion', 'ingresos_totales', 'monto_solicitado', 'plazo_solicitado',
        ]
        widgets = {
            'fecha_nacimiento': forms.DateInput(attrs={'type': 'date'}),
            'fecha_expedicion': forms.DateInput(attrs={'type': 'date'}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})

# --- FORMULARIO 2: Para que el Asesor suba documentos iniciales ---
class DocumentoForm(forms.ModelForm):
    """
    Formulario para que el Asesor suba los documentos iniciales del cliente.
    """
    class Meta:
        model = Documento
        fields = ['nombre_documento', 'archivo']
        widgets = {
            'nombre_documento': forms.Select(attrs={'class': 'form-select'}),
            'archivo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtramos las opciones para mostrar solo las del asesor
        opciones_asesor = next(
            (grupo[1] for grupo in Documento.DOCUMENTOS_CHOICES if grupo[0] == 'Documentos del Asesor'),
            []
        )
        self.fields['nombre_documento'].choices = opciones_asesor
        self.fields['nombre_documento'].label = "Tipo de Documento"


# --- FORMULARIO 3: Para que el Analista suba sus documentos de análisis ---
class DocumentoAnalisisForm(forms.ModelForm):
    """
    Formulario para que el analista suba sus documentos de análisis.
    """
    class Meta:
        model = Documento
        fields = ['nombre_documento', 'archivo']
        widgets = {
            'nombre_documento': forms.Select(attrs={'class': 'form-select'}),
            'archivo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtramos las opciones para mostrar solo las del analista
        opciones_analista = next(
            (grupo[1] for grupo in Documento.DOCUMENTOS_CHOICES if grupo[0] == 'Documentos de Análisis'),
            []
        )
        self.fields['nombre_documento'].choices = opciones_analista
        self.fields['nombre_documento'].label = "Tipo de Documento de Análisis"


# --- FORMULARIO PARA LA OBSERVACIÓN DE DOCUMENTOS (CORREGIDO) ---
# Este formulario se usará en la pestaña 1 del dashboard del analista
class ObservacionAnalisisForm(forms.ModelForm):
    class Meta:
        model = SolicitudCredito
        fields = ['observacion_analisis_documentos']
        labels = {
            'observacion_analisis_documentos': 'Observación General sobre los Documentos de Análisis'
        }
        widgets = {
            'observacion_analisis_documentos': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }

# --- FORMULARIO 4: Para el Análisis de Riesgo (Pestaña 2 del Analista) ---
class AnalisisRiesgoForm(forms.ModelForm):
    class Meta:
        model = SolicitudCredito
        fields = [
            'mora_telco_mayor_300k', 'mora_otros_mayor_500k', 'es_tipo_0',
            'huellas_consulta', 'tiene_procesos_judiciales',
        ]
        widgets = {
            'mora_telco_mayor_300k': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'mora_otros_mayor_500k': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'es_tipo_0': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'tiene_procesos_judiciales': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

# --- FORMULARIO 5: Para el Análisis de Capacidad de Pago ---
class CapacidadPagoForm(forms.ModelForm):
    class Meta:
        model = SolicitudCredito
        fields = [
            'ingresos_totales', 'gastos_personales', 'gastos_financieros',
            'tipo_vivienda', 'num_aportantes', 'personas_a_cargo',
            'direccion_residencia', 'ciudad_residencia', 'departamento_residencia',
            'barrio_residencia', 'estrato', 'estado_civil', 'sexo',
        ]
        widgets = {
            'tipo_vivienda': forms.Select(attrs={'class': 'form-select'}),
            'num_aportantes': forms.Select(attrs={'class': 'form-select'}),
            'personas_a_cargo': forms.Select(attrs={'class': 'form-select'}),
            'estado_civil': forms.Select(attrs={'class': 'form-select'}),
            'sexo': forms.Select(attrs={'class': 'form-select'}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if not isinstance(field.widget, forms.Select):
                field.widget.attrs.update({'class': 'form-control'})

# --- FORMULARIO 6: Para la Calculadora/Simulador de Oferta ---
class OfertaForm(forms.ModelForm):
    class Meta:
        model = SolicitudCredito
        fields = ['plazo_oferta']
        widgets = {
            'plazo_oferta': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 24'})
        }

# --- FORMULARIO 7: Para registrar la Oferta Definitiva ---
class OfertaDefinitivaForm(forms.ModelForm):
    class Meta:
        model = SolicitudCredito
        fields = ['monto_aprobado_calculado', 'plazo_oferta', 'observacion_oferta_final']
        labels = {
            'monto_aprobado_calculado': 'Monto Definitivo Aprobado',
            'plazo_oferta': 'Plazo Definitivo (meses)',
            'observacion_oferta_final': 'Observaciones / Justificación de la Oferta'
        }
        widgets = {
            'observacion_oferta_final': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

# --- FORMULARIO 8: Para registrar las Referencias (Fase Futura) ---
class ReferenciaForm(forms.ModelForm):
    class Meta:
        model = Referencia
        fields = ['tipo', 'nombre_completo', 'numero_contacto', 'parentesco']
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'nombre_completo': forms.TextInput(attrs={'class': 'form-control'}),
            'numero_contacto': forms.TextInput(attrs={'class': 'form-control'}),
            'parentesco': forms.TextInput(attrs={'class': 'form-control'}),
        }




class RechazoDocumentoForm(forms.ModelForm):
    """
    Formulario para que el analista ingrese la razón del rechazo de un documento.
    """
    class Meta:
        model = Documento
        fields = ['observacion_correccion']
        widgets = {
            'observacion_correccion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Ej: La imagen de la cédula está borrosa, por favor, vuelva a subirla con mejor calidad.'
            }),
        }
        labels = {
            'observacion_correccion': 'Motivo de la Corrección'
        }


class DocumentoFinalForm(forms.ModelForm):
    """
    Formulario para que el Asesor suba los documentos finales de cierre.
    """
    class Meta:
        model = Documento
        fields = ['nombre_documento', 'archivo']
        widgets = {
            'nombre_documento': forms.Select(attrs={'class': 'form-select'}),
            'archivo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtramos las opciones para mostrar solo las de cierre
        opciones_cierre = next(
            (grupo[1] for grupo in Documento.DOCUMENTOS_CHOICES if grupo[0] == 'Documentos de Cierre'),
            []
        )
        self.fields['nombre_documento'].choices = opciones_cierre
        self.fields['nombre_documento'].label = "Tipo de Documento Final"



class ParametrosGlobalesForm(forms.ModelForm):
    class Meta:
        model = ParametrosGlobales
        fields = ['smlv', 'tasa_interes_mensual', 'porcentaje_seguro', 'porcentaje_fgs']
        labels = {
            'smlv': 'Valor del Salario Mínimo (SMLV)',
            'tasa_interes_mensual': 'Tasa de Interés Mensual (Ej: 0.023 para 2.3%)',
            'porcentaje_seguro': 'Porcentaje del Seguro (Ej: 0.0025 para 0.25%)',
            'porcentaje_fgs': 'Porcentaje del Fondo de Garantías (Ej: 0.0025 para 0.25%)',
        }
        help_texts = {
            'tasa_interes_mensual': 'Use punto como separador decimal.',
            'porcentaje_seguro': 'Use punto como separador decimal.',
            'porcentaje_fgs': 'Use punto como separador decimal.',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})



class ObservacionReferenciasForm(forms.ModelForm):
    """
    Formulario para que el analista ingrese sus observaciones
    después de validar las referencias.
    """
    class Meta:
        model = SolicitudCredito
        # Usamos el campo que ya existía en el modelo
        fields = ['observacion_referencias']
        labels = {
            'observacion_referencias': 'Observación General de Referencias'
        }
        widgets = {
            'observacion_referencias': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }




class HistorialFiltroForm(forms.Form):
    """
    Un formulario que no está ligado a un modelo, usado para
    capturar los criterios de búsqueda en el historial.
    """
    # Creamos un campo de estado, añadiendo una opción para "Todos"
    ESTADOS_CHOICES = [('', 'Todos los Estados')] + SolicitudCredito.ESTADOS_CHOICES
    estado = forms.ChoiceField(choices=ESTADOS_CHOICES, required=False, widget=forms.Select(attrs={'class': 'form-select'}))
    
    # Creamos campos para filtrar por fechas
    fecha_inicio = forms.DateField(required=False, widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}))
    fecha_fin = forms.DateField(required=False, widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}))

    # Creamos campos para filtrar por usuario (Asesor y Analista)
    # Usamos ModelChoiceField para crear un menú desplegable con los usuarios
    asesor = forms.ModelChoiceField(
        queryset=User.objects.filter(perfil__rol='ASESOR'),
        required=False,
        empty_label="Todos los Asesores",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    analista = forms.ModelChoiceField(
        queryset=User.objects.filter(perfil__rol='ANALISTA'),
        required=False,
        empty_label="Todos los Analistas",
        widget=forms.Select(attrs={'class': 'form-select'})
    )



class AnalistaHistorialFiltroForm(forms.Form):
    """
    Un formulario para que el analista filtre su historial de casos atendidos.
    """
    # Creamos un campo de estado, con los estados finales relevantes
    ESTADOS_FINALES_CHOICES = [
        ('', 'Todos los Estados'),
        (SolicitudCredito.ESTADO_RECHAZADO_ANALISTA, 'Rechazado por mí'),
        (SolicitudCredito.ESTADO_APROBADO, 'Aprobado por Director'),
        (SolicitudCredito.ESTADO_RECHAZADO_DIRECTOR, 'Rechazado por Director'),
    ]
    estado = forms.ChoiceField(
        label="Estado Final",
        choices=ESTADOS_FINALES_CHOICES, 
        required=False, 
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    # Creamos campos para filtrar por rango de fechas
    fecha_inicio = forms.DateField(
        label="Desde",
        required=False, 
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    fecha_fin = forms.DateField(
        label="Hasta",
        required=False, 
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )


class CrearUsuarioForm(forms.Form):
    """
    Formulario para que el Director cree nuevos usuarios, ahora incluyendo el teléfono.
    """
    username = forms.CharField(label="Nombre de Usuario (único)", max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
    first_name = forms.CharField(label="Nombres", max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(label="Apellidos", max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(label="Correo Electrónico", widget=forms.EmailInput(attrs={'class': 'form-control'}))
    
    # --- CAMPO AÑADIDO ---
    telefono = forms.CharField(label="Número de Teléfono", max_length=20, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    
    password = forms.CharField(label="Contraseña Temporal", widget=forms.PasswordInput(attrs={'class': 'form-control'}))



class AsesorHistorialFiltroForm(forms.Form):
    """
    Un formulario para que el asesor filtre su propia lista de solicitudes.
    """
    # Creamos un campo de estado, añadiendo una opción para "Todos"
    ESTADOS_CHOICES = [('', 'Todos los Estados')] + SolicitudCredito.ESTADOS_CHOICES
    estado = forms.ChoiceField(
        label="Estado",
        choices=ESTADOS_CHOICES, 
        required=False, 
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    # Creamos campos para filtrar por rango de fechas
    fecha_inicio = forms.DateField(
        label="Desde",
        required=False, 
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    fecha_fin = forms.DateField(
        label="Hasta",
        required=False, 
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )