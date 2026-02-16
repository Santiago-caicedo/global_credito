# creditos/views_publico.py
"""
Vistas públicas para solicitud de crédito y área privada del aspirante.
"""
import secrets
from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.contrib import messages
from django.utils import timezone

from usuarios.models import PerfilUsuario
from .models import SolicitudCredito, Documento, HistorialEstado, NotificacionEmail
from .forms import (
    SolicitudPublicaForm, AspiranteRegistroForm,
    DocumentoForm, DocumentoFinalForm
)
from .decorators import aspirante_required
from .services import ejecutar_motor_inicial, asignar_solicitud_a_analista, enviar_notificacion_email
from .datacredito_service import consultar_datacredito, actualizar_solicitud_con_datacredito


# ==============================================================================
# VISTAS PÚBLICAS (Sin autenticación requerida)
# ==============================================================================

def aplicar_credito_view(request):
    """
    Formulario público para solicitar crédito.
    Flujo: llenar datos → confirmar → mostrar página genérica → enviar email según resultado
    """
    action = request.POST.get('action', 'input')

    # Paso 2: Revisión de datos
    if request.method == 'POST' and action == 'review':
        form = SolicitudPublicaForm(request.POST)
        if form.is_valid():
            # Preparar datos para confirmación
            confirmation_data = []
            for name, value in form.cleaned_data.items():
                field = form.fields[name]
                display_value = value
                if hasattr(field, 'choices') and field.choices:
                    display_value = dict(field.choices).get(value, value)
                confirmation_data.append({
                    'label': field.label,
                    'value': display_value,
                    'name': name,
                })

            return render(request, 'creditos/publico/aplicar.html', {
                'form': form,
                'confirmation_mode': True,
                'confirmation_data': confirmation_data,
            })
        else:
            return render(request, 'creditos/publico/aplicar.html', {'form': form})

    # Paso 3: Confirmación final
    elif request.method == 'POST' and action == 'confirm':
        form = SolicitudPublicaForm(request.POST)
        if form.is_valid():
            cedula = form.cleaned_data.get('cedula')
            email = form.cleaned_data.get('email_aspirante')

            # Verificar si ya existe una solicitud con esta cedula (inactiva)
            estados_inactivos = [
                SolicitudCredito.ESTADO_RECHAZADO_AUTO,
                SolicitudCredito.ESTADO_RECHAZADO_ANALISTA,
                SolicitudCredito.ESTADO_RECHAZADO_DIRECTOR,
                SolicitudCredito.ESTADO_APROBADO,
            ]
            solicitud_existente = SolicitudCredito.objects.filter(
                cedula=cedula,
                estado__in=estados_inactivos
            ).first()

            if solicitud_existente:
                # ACTUALIZAR solicitud existente (reaplicacion)
                solicitud = solicitud_existente
                estado_anterior = solicitud.estado

                # Actualizar todos los campos del formulario
                for field, value in form.cleaned_data.items():
                    setattr(solicitud, field, value)

                # Resetear campos de analisis previo
                solicitud.estado = SolicitudCredito.ESTADO_NUEVO
                solicitud.aspirante = None
                solicitud.analista_asignado = None
                solicitud.recomendacion_sistema_aprobada = None
                solicitud.recomendacion_sistema_texto = None
                solicitud.monto_aprobado_calculado = None
                solicitud.plazo_oferta = None
                solicitud.capacidad_pago_calculada = None
                solicitud.save()

                # Registrar reaplicacion en historial
                HistorialEstado.objects.create(
                    solicitud=solicitud,
                    estado_anterior=estado_anterior,
                    estado_nuevo=solicitud.estado,
                    observaciones="Reaplicacion: Usuario volvio a aplicar despues de rechazo/aprobacion anterior."
                )
            else:
                # CREAR nueva solicitud
                solicitud = form.save(commit=False)
                solicitud.save()

                # Registrar creacion en historial
                HistorialEstado.objects.create(
                    solicitud=solicitud,
                    estado_nuevo=solicitud.estado,
                    observaciones="Solicitud creada desde formulario publico."
                )

            # Ejecutar motor inicial (edad, ingresos)
            nuevo_estado, observacion_motor = ejecutar_motor_inicial(solicitud)
            estado_anterior = solicitud.estado
            solicitud.estado = nuevo_estado
            solicitud.save()

            # Registrar resultado del motor inicial
            HistorialEstado.objects.create(
                solicitud=solicitud,
                estado_anterior=estado_anterior,
                estado_nuevo=nuevo_estado,
                observaciones=f"Motor inicial: {observacion_motor}"
            )

            # Preparar URLs para los emails
            site_url = request.build_absolute_uri('/').rstrip('/')
            url_aplicar = f"{site_url}/aplicar/"

            # Si fue rechazado por motor inicial
            if nuevo_estado == SolicitudCredito.ESTADO_RECHAZADO_AUTO:
                enviar_notificacion_email(
                    solicitud,
                    NotificacionEmail.TIPO_RECHAZO_MOTOR,
                    extra_context={
                        'url_aplicar': url_aplicar,
                        'site_url': site_url,
                    }
                )
            else:
                # PASO 2: Consulta a DataCrédito (después del motor inicial)
                resultado_dc = consultar_datacredito(solicitud)

                # Actualizar solicitud con datos de DataCrédito
                actualizar_solicitud_con_datacredito(solicitud, resultado_dc)

                # Verificar si DataCrédito recomienda rechazar
                if resultado_dc.get('rechazar'):
                    # Registrar rechazo por DataCrédito
                    estado_anterior = solicitud.estado
                    solicitud.estado = SolicitudCredito.ESTADO_RECHAZADO_AUTO
                    solicitud.save()

                    HistorialEstado.objects.create(
                        solicitud=solicitud,
                        estado_anterior=estado_anterior,
                        estado_nuevo=solicitud.estado,
                        observaciones=f"Motor DataCrédito: {resultado_dc.get('motivo_rechazo', 'Rechazado por política de riesgo')}"
                    )

                    # Enviar email de rechazo (genérico, sin revelar motivo)
                    enviar_notificacion_email(
                        solicitud,
                        NotificacionEmail.TIPO_RECHAZO_MOTOR,
                        extra_context={
                            'url_aplicar': url_aplicar,
                            'site_url': site_url,
                        }
                    )
                else:
                    # Si pasó ambos motores, generar token de registro
                    solicitud.token_registro = secrets.token_urlsafe(32)
                    solicitud.token_expiracion = timezone.now() + timedelta(hours=24)
                    solicitud.save()

                    # Construir URL de registro con token
                    url_registro = f"{site_url}/aplicar/registro/{solicitud.token_registro}/"

                    # Enviar email de pre-aprobación con enlace
                    enviar_notificacion_email(
                        solicitud,
                        NotificacionEmail.TIPO_PREAPROBACION,
                        extra_context={
                            'url_registro': url_registro,
                            'site_url': site_url,
                        }
                    )

            # Siempre mostrar página genérica de "datos recibidos"
            return render(request, 'creditos/publico/solicitud_recibida.html', {
                'email': email,
            })

    # Paso 1: Mostrar formulario vacío o con datos editados
    form = SolicitudPublicaForm(request.POST if action == 'edit' else None)
    return render(request, 'creditos/publico/aplicar.html', {'form': form})


def aplicar_rechazado_view(request, solicitud_id):
    """
    Página que muestra el rechazo automático al aspirante.
    """
    solicitud = get_object_or_404(SolicitudCredito, id=solicitud_id)

    # Solo mostrar si realmente fue rechazado automáticamente
    if solicitud.estado != SolicitudCredito.ESTADO_RECHAZADO_AUTO:
        return redirect('aplicar_credito')

    # Obtener razón del rechazo del historial
    historial = solicitud.historial.filter(
        estado_nuevo=SolicitudCredito.ESTADO_RECHAZADO_AUTO
    ).first()
    razon = historial.observaciones if historial else "No cumple con los requisitos mínimos."

    return render(request, 'creditos/publico/rechazado.html', {
        'solicitud': solicitud,
        'razon': razon,
    })


def aspirante_registro_view(request, token):
    """
    Formulario para que el aspirante cree sus credenciales
    después de pasar el motor inicial.
    El token se recibe por URL desde el email de pre-aprobación.
    """
    # Validar que el token existe
    if not token:
        messages.error(request, "Enlace inválido. Por favor, inicia una nueva solicitud.")
        return redirect('aplicar_credito')

    # Buscar solicitud por token
    solicitud = get_object_or_404(
        SolicitudCredito,
        token_registro=token
    )

    # Validar que el token no haya expirado
    if solicitud.token_expiracion and solicitud.token_expiracion < timezone.now():
        messages.error(request, "El enlace de registro ha expirado. Por favor, inicia una nueva solicitud.")
        return redirect('aplicar_credito')

    # Validar que la solicitud no tenga ya un usuario asignado
    if solicitud.aspirante:
        messages.info(request, "Ya tienes una cuenta creada. Por favor, inicia sesión.")
        return redirect('login')

    if request.method == 'POST':
        form = AspiranteRegistroForm(request.POST)
        if form.is_valid():
            # Crear usuario
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password1'],
                email=solicitud.email_aspirante,
                first_name=solicitud.nombre_completo.split()[0] if solicitud.nombre_completo else '',
                last_name=' '.join(solicitud.nombre_completo.split()[1:]) if solicitud.nombre_completo else '',
            )

            # Crear perfil de aspirante
            PerfilUsuario.objects.create(
                usuario=user,
                rol=PerfilUsuario.ROL_ASPIRANTE,
                telefono=solicitud.telefono_aspirante,
            )

            # Vincular solicitud al usuario
            solicitud.aspirante = user
            solicitud.token_registro = None
            solicitud.token_expiracion = None
            solicitud.save()

            # Registrar en historial
            HistorialEstado.objects.create(
                solicitud=solicitud,
                estado_anterior=solicitud.estado,
                estado_nuevo=solicitud.estado,
                usuario_responsable=user,
                observaciones="Aspirante registrado exitosamente en el sistema."
            )

            # Enviar email de bienvenida
            site_url = request.build_absolute_uri('/').rstrip('/')
            enviar_notificacion_email(
                solicitud,
                NotificacionEmail.TIPO_BIENVENIDA,
                extra_context={'site_url': site_url}
            )

            # Iniciar sesión automáticamente
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')

            messages.success(
                request,
                f"Bienvenido/a {user.first_name}! Tu cuenta ha sido creada exitosamente. "
                "Ahora debes cargar los documentos requeridos para continuar con tu solicitud."
            )
            return redirect('aspirante_escritorio')
    else:
        form = AspiranteRegistroForm()

    return render(request, 'creditos/publico/registro.html', {
        'form': form,
        'solicitud': solicitud,
    })


# ==============================================================================
# VISTAS PRIVADAS DEL ASPIRANTE (Autenticación requerida)
# ==============================================================================

@login_required
@aspirante_required
def aspirante_escritorio_view(request):
    """
    Dashboard principal del aspirante donde ve el estado de su solicitud
    y puede gestionar documentos.
    """
    # Obtener la solicitud del aspirante
    solicitud = SolicitudCredito.objects.filter(aspirante=request.user).first()

    if not solicitud:
        messages.error(request, "No tiene ninguna solicitud asociada a su cuenta.")
        return redirect('login')

    # Determinar el formulario de documentos según el estado
    estados_docs_iniciales = [
        SolicitudCredito.ESTADO_PEND_DOCUMENTOS,
        SolicitudCredito.ESTADO_DOCS_CORRECCION,
    ]
    estados_docs_finales = [
        SolicitudCredito.ESTADO_PEND_DOCS_ADICIONALES,
        SolicitudCredito.ESTADO_DOCS_FINALES_CORRECCION,
    ]

    form_documento = None
    if solicitud.estado in estados_docs_iniciales:
        form_documento = DocumentoForm()
    elif solicitud.estado in estados_docs_finales:
        form_documento = DocumentoFinalForm()

    # Obtener documentos cargados por el aspirante
    documentos = solicitud.documentos.filter(subido_por=request.user).order_by('-fecha_carga')

    # Verificar si hay documentos que necesitan corrección
    docs_con_error = documentos.filter(ok_analista=False)
    necesita_correccion = docs_con_error.exists()

    # Determinar qué documentos se requieren según el estado
    if solicitud.estado in estados_docs_iniciales:
        tipos_requeridos = {'CEDULA', 'DECLARACION_RENTA', 'CERTIFICADO_LABORAL', 'AUTORIZACION_CONSULTA'}
    elif solicitud.estado in estados_docs_finales:
        tipos_requeridos = {'PAGARE', 'CARTA_INSTRUCCIONES', 'POLIZA_SEGURO', 'FORMATO_VINCULACION'}
    else:
        tipos_requeridos = set()

    # Tipos ya cargados (solo los que están OK)
    tipos_cargados = set(documentos.filter(ok_analista=True).values_list('nombre_documento', flat=True))
    documentos_completos = tipos_requeridos.issubset(tipos_cargados)

    # Historial reciente
    historial = solicitud.historial.all()[:10]

    return render(request, 'creditos/aspirante/escritorio.html', {
        'solicitud': solicitud,
        'form_documento': form_documento,
        'documentos': documentos,
        'docs_con_error': docs_con_error,
        'necesita_correccion': necesita_correccion,
        'documentos_completos': documentos_completos,
        'tipos_requeridos': tipos_requeridos,
        'tipos_cargados': tipos_cargados,
        'historial': historial,
    })


@login_required
@aspirante_required
def aspirante_subir_documento_view(request):
    """
    Procesa la subida de documentos por el aspirante.
    """
    if request.method != 'POST':
        return redirect('aspirante_escritorio')

    solicitud = get_object_or_404(SolicitudCredito, aspirante=request.user)

    # Determinar el formulario según el estado
    estados_docs_iniciales = [
        SolicitudCredito.ESTADO_PEND_DOCUMENTOS,
        SolicitudCredito.ESTADO_DOCS_CORRECCION,
    ]
    estados_docs_finales = [
        SolicitudCredito.ESTADO_PEND_DOCS_ADICIONALES,
        SolicitudCredito.ESTADO_DOCS_FINALES_CORRECCION,
    ]

    if solicitud.estado in estados_docs_iniciales:
        form = DocumentoForm(request.POST, request.FILES)
    elif solicitud.estado in estados_docs_finales:
        form = DocumentoFinalForm(request.POST, request.FILES)
    else:
        messages.error(request, "Su solicitud no está en una etapa que permita cargar documentos.")
        return redirect('aspirante_escritorio')

    if form.is_valid():
        documento = form.save(commit=False)
        documento.solicitud = solicitud
        documento.subido_por = request.user
        documento.ok_analista = True
        documento.observacion_correccion = ""
        documento.save()
        messages.success(request, f"Documento '{documento.get_nombre_documento_display()}' cargado exitosamente.")
    else:
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f"{error}")

    return redirect('aspirante_escritorio')


@login_required
@aspirante_required
def aspirante_eliminar_documento_view(request, documento_id):
    """
    Permite al aspirante eliminar un documento que subió.
    """
    if request.method != 'POST':
        return redirect('aspirante_escritorio')

    documento = get_object_or_404(Documento, id=documento_id, subido_por=request.user)
    solicitud = documento.solicitud

    # Verificar que la solicitud pertenece al aspirante
    if solicitud.aspirante != request.user:
        messages.error(request, "No tiene permiso para eliminar este documento.")
        return redirect('aspirante_escritorio')

    # Estados en los que se puede eliminar documentos
    estados_editables = [
        SolicitudCredito.ESTADO_PEND_DOCUMENTOS,
        SolicitudCredito.ESTADO_DOCS_CORRECCION,
        SolicitudCredito.ESTADO_PEND_DOCS_ADICIONALES,
        SolicitudCredito.ESTADO_DOCS_FINALES_CORRECCION,
    ]

    if solicitud.estado in estados_editables:
        nombre = documento.get_nombre_documento_display()
        documento.delete()
        messages.success(request, f"Documento '{nombre}' eliminado correctamente.")
    else:
        messages.error(request, "No puede eliminar documentos en esta etapa del proceso.")

    return redirect('aspirante_escritorio')


@login_required
@aspirante_required
def aspirante_enviar_documentos_view(request):
    """
    Envía los documentos cargados para revisión del analista.
    """
    if request.method != 'POST':
        return redirect('aspirante_escritorio')

    solicitud = get_object_or_404(SolicitudCredito, aspirante=request.user)

    # Envío de documentos iniciales
    if solicitud.estado in [SolicitudCredito.ESTADO_PEND_DOCUMENTOS, SolicitudCredito.ESTADO_DOCS_CORRECCION]:
        estado_anterior = solicitud.estado
        solicitud.estado = SolicitudCredito.ESTADO_EN_ASIGNACION
        solicitud.save()

        HistorialEstado.objects.create(
            solicitud=solicitud,
            estado_anterior=estado_anterior,
            estado_nuevo=solicitud.estado,
            usuario_responsable=request.user,
            observaciones="Aspirante envió documentos iniciales para análisis."
        )

        # Intentar asignar a un analista disponible
        asignar_solicitud_a_analista(solicitud.id)

        messages.success(
            request,
            "Sus documentos han sido enviados para revisión. "
            "Le notificaremos por correo electrónico cuando haya novedades."
        )

    # Envío de documentos finales
    elif solicitud.estado in [SolicitudCredito.ESTADO_PEND_DOCS_ADICIONALES, SolicitudCredito.ESTADO_DOCS_FINALES_CORRECCION]:
        estado_anterior = solicitud.estado
        solicitud.estado = SolicitudCredito.ESTADO_EN_VALIDACION_DOCS
        solicitud.save()

        HistorialEstado.objects.create(
            solicitud=solicitud,
            estado_anterior=estado_anterior,
            estado_nuevo=solicitud.estado,
            usuario_responsable=request.user,
            observaciones="Aspirante envió documentos finales para validación."
        )

        messages.success(
            request,
            "Sus documentos finales han sido enviados para validación. "
            "Le notificaremos cuando el proceso esté completo."
        )
    else:
        messages.error(request, "Su solicitud no está en una etapa que permita enviar documentos.")

    return redirect('aspirante_escritorio')


@login_required
@aspirante_required
def aspirante_corregir_documento_view(request, documento_id):
    """
    Elimina un documento marcado para corrección para que el aspirante pueda subir uno nuevo.
    """
    if request.method != 'POST':
        return redirect('aspirante_escritorio')

    documento = get_object_or_404(Documento, id=documento_id, subido_por=request.user)
    solicitud = documento.solicitud

    # Verificar que la solicitud pertenece al aspirante
    if solicitud.aspirante != request.user:
        messages.error(request, "No tiene permiso para modificar este documento.")
        return redirect('aspirante_escritorio')

    # Solo permitir corregir si el documento fue marcado para corrección
    if not documento.ok_analista:
        nombre = documento.get_nombre_documento_display()
        documento.delete()
        messages.info(request, f"Documento '{nombre}' eliminado. Por favor, suba la versión corregida.")
    else:
        messages.warning(request, "Este documento no requiere corrección.")

    return redirect('aspirante_escritorio')
