from django import forms
from .models import SolicitudCredito, Documento, Referencia


class SolicitudCreditoForm(forms.ModelForm):
    class Meta:
        model = SolicitudCredito
        # Esta es la lista de campos correcta y actualizada
        fields = [
            'cedula',
            'nombre_completo',
            'fecha_nacimiento',
            'fecha_expedicion',
            'ocupacion',
            'ingresos_totales',
        ]
        
        # Widgets para mejorar la experiencia del usuario
        widgets = {
            'fecha_nacimiento': forms.DateInput(attrs={'type': 'date', 'required': True}),
            'fecha_expedicion': forms.DateInput(attrs={'type': 'date', 'required': True}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Este bucle añade la clase 'form-control' a todos los campos
        # para que se vean bien con Bootstrap.
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})


class DocumentoForm(forms.ModelForm):
    class Meta:
        model = Documento
        fields = ['nombre_documento', 'archivo']
        widgets = {
            # Podemos añadir estilos si queremos
            'nombre_documento': forms.Select(attrs={'class': 'form-select'}),
            'archivo': forms.ClearableFileInput(attrs={'class': 'form-control'})
        }




class ObservacionesAnalistaForm(forms.ModelForm):
    """
    Formulario para que el analista ingrese sus observaciones.
    """
    class Meta:
        model = SolicitudCredito
        # Campos que el analista puede editar en esta fase
        fields = [
            'observacion_centrales_riesgo',
            'observacion_llamada_cliente'
        ]
        widgets = {
            'observacion_centrales_riesgo': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'observacion_llamada_cliente': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }

class ReferenciaForm(forms.ModelForm):
    """
    Formulario para añadir una nueva referencia a la solicitud.
    """
    class Meta:
        model = Referencia
        fields = ['tipo', 'nombre_completo', 'numero_contacto', 'parentesco']
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'nombre_completo': forms.TextInput(attrs={'class': 'form-control'}),
            'numero_contacto': forms.TextInput(attrs={'class': 'form-control'}),
            'parentesco': forms.TextInput(attrs={'class': 'form-control'}),
        }




class DocumentoAnalisisForm(forms.ModelForm):
    # Definimos los tipos de documentos que el analista puede subir
    DOCUMENTOS_ANALISTA_CHOICES = [
        ('HISTORIAL_CREDITO', 'Historial de Crédito (PDF)'),
        ('PROCESOS_JUDICIALES', 'Pantallazo de Procesos Judiciales'),
        ('ADRESS', 'Pantallazo ADRESS'),
        ('CONTRALORIA', 'Antecedentes en Contraloría (PDF)'),
        ('PROCURADURIA', 'Antecedentes en Procuraduría (Pantallazo)'),
        ('OTRAS_CONSULTAS', 'Otras Consultas (Puesto de Votación, Sisbén)'),
    ]
    nombre_documento = forms.ChoiceField(choices=DOCUMENTOS_ANALISTA_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))

    class Meta:
        model = Documento
        fields = ['nombre_documento', 'archivo']

# Formulario para la observación general de los documentos de análisis
class ObservacionAnalisisForm(forms.ModelForm):
    class Meta:
        model = SolicitudCredito
        fields = ['observacion_analisis_documentos']
        widgets = {
            'observacion_analisis_documentos': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }

# Formulario para que el analista ingrese los datos para el motor de recomendación
class AnalisisRiesgoForm(forms.ModelForm):
    class Meta:
        model = SolicitudCredito
        # Campos que el analista llena manualmente
        fields = [
            'mora_telco_mayor_300k',
            'mora_otros_mayor_500k',
            'es_tipo_0',
            'huellas_consulta',
            'tiene_procesos_judiciales',
        ]
        # Usamos checkboxes para los booleanos
        widgets = {
            'mora_telco_mayor_300k': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'mora_otros_mayor_500k': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'es_tipo_0': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'tiene_procesos_judiciales': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }



class CapacidadPagoForm(forms.ModelForm):
    """
    Formulario completo para que el analista recopile toda la información
    demográfica y financiera del cliente.
    """
    class Meta:
        model = SolicitudCredito
        fields = [
            'ingresos_totales',
            'gastos_personales',
            'gastos_financieros',
            'tipo_vivienda',
            'num_aportantes',
            'personas_a_cargo',
            'direccion_residencia',
            'ciudad_residencia',
            'departamento_residencia',
            'barrio_residencia',
            'estrato',
            'estado_civil',
            'sexo',
        ]
        # Widgets para que el formulario se vea bien con Bootstrap
        widgets = {
            'tipo_vivienda': forms.Select(attrs={'class': 'form-select'}),
            'num_aportantes': forms.Select(attrs={'class': 'form-select'}),
            'personas_a_cargo': forms.Select(attrs={'class': 'form-select'}),
            'estado_civil': forms.Select(attrs={'class': 'form-select'}),
            'sexo': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Bucle para añadir la clase 'form-control' a la mayoría de los campos
        for field_name, field in self.fields.items():
            if not isinstance(field.widget, forms.Select):
                field.widget.attrs.update({'class': 'form-control'})