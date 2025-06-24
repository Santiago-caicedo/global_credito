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