# En tu archivo: creditos/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from decimal import Decimal
from .models import SolicitudCredito, Documento, HistorialEstado
from .forms import (
    ObservacionAnalisisForm, RechazoDocumentoForm, SolicitudCreditoForm, DocumentoForm, DocumentoAnalisisForm,
    AnalisisRiesgoForm, CapacidadPagoForm, OfertaForm, OfertaDefinitivaForm
)
from .services import (
    ejecutar_motor_inicial, asignar_solicitud_a_analista,
    ejecutar_motor_recomendacion, calcular_capacidad_pago_service,
    calcular_oferta_service, intentar_asignar_solicitud_en_espera
)


# ==============================================================================
# VISTAS DEL ASESOR
# ==============================================================================

@login_required
def crear_solicitud_view(request):
    if request.method == 'POST':
        form = SolicitudCreditoForm(request.POST)
        if form.is_valid():
            solicitud = form.save(commit=False)
            solicitud.asesor_comercial = request.user
            solicitud.save()

            HistorialEstado.objects.create(
                solicitud=solicitud,
                estado_nuevo=solicitud.estado,
                usuario_responsable=request.user,
                observaciones="Creación de la solicitud por asesor."
            )
            
            nuevo_estado, observacion_motor = ejecutar_motor_inicial(solicitud)
            
            estado_anterior = solicitud.estado
            solicitud.estado = nuevo_estado
            solicitud.save()

            HistorialEstado.objects.create(
                solicitud=solicitud,
                estado_anterior=estado_anterior,
                estado_nuevo=nuevo_estado,
                usuario_responsable=None,
                observaciones=f"Resultado del motor inicial: {observacion_motor}"
            )
            
            messages.success(request, f"Solicitud #{solicitud.id} ha sido creada y procesada exitosamente.")
            return redirect('listar_solicitudes')
        else:
            messages.error(request, "Error al crear la solicitud. Por favor, revise los campos obligatorios.")
    else:
        form = SolicitudCreditoForm()
        
    return render(request, 'creditos/crear_solicitud.html', {'form': form})


@login_required
def listar_solicitudes_view(request):
    solicitudes_del_asesor = SolicitudCredito.objects.filter(asesor_comercial=request.user)
    return render(request, 'creditos/listar_solicitudes.html', {'solicitudes': solicitudes_del_asesor})


@login_required
def solicitud_detalle_view(request, solicitud_id):
    solicitud = get_object_or_404(SolicitudCredito, id=solicitud_id)
    
    if request.user != solicitud.asesor_comercial:
        messages.error(request, "No tienes permiso para ver esta solicitud.")
        return redirect('listar_solicitudes')

    # Lógica de POST para subir un nuevo documento
    if request.method == 'POST':
        form = DocumentoForm(request.POST, request.FILES)
        if form.is_valid():
            nuevo_documento = form.save(commit=False)
            nuevo_documento.solicitud = solicitud
            nuevo_documento.subido_por = request.user
            nuevo_documento.save()
            messages.success(request, f"Documento '{nuevo_documento.get_nombre_documento_display()}' cargado exitosamente.")
        else:
            messages.error(request, "Error al cargar el documento. Por favor, intente de nuevo.")
        return redirect('solicitud_detalle', solicitud_id=solicitud.id)

    # Lógica de GET para mostrar la página
    form_documento = DocumentoForm()
    documentos_cargados = solicitud.documentos.filter(subido_por=request.user)
    
    # Comprobamos si hay documentos que necesiten corrección
    documentos_a_corregir = documentos_cargados.filter(ok_analista=False)
    
    contexto = {
        'solicitud': solicitud,
        'form_documento': form_documento,
        'documentos_cargados': documentos_cargados,
        'necesita_correccion': documentos_a_corregir.exists(),
    }
    return render(request, 'creditos/solicitud_detalle.html', contexto)



@login_required
def enviar_a_asignacion_view(request, solicitud_id):
    if request.method == 'POST':
        solicitud = get_object_or_404(SolicitudCredito, id=solicitud_id)
        
        if request.user != solicitud.asesor_comercial:
            messages.error(request, "Acción no permitida.")
            return redirect('solicitud_detalle', solicitud_id=solicitud.id)
            
        estado_anterior = solicitud.estado
        solicitud.estado = SolicitudCredito.ESTADO_EN_ASIGNACION
        solicitud.save()
        
        HistorialEstado.objects.create(
            solicitud=solicitud,
            estado_anterior=estado_anterior,
            estado_nuevo=solicitud.estado,
            usuario_responsable=request.user,
            observaciones="Asesor envió la solicitud para asignación de analista."
        )

        asignar_solicitud_a_analista(solicitud.id)
        messages.info(request, f"Solicitud #{solicitud.id} enviada a la cola de asignación.")
    
    return redirect('solicitud_detalle', solicitud_id=solicitud.id)


# ==============================================================================
# VISTAS DEL ANALISTA
# ==============================================================================

@login_required
def analista_dashboard_view(request):
    # 1. Verificación inicial del perfil y la solicitud asignada
    if not hasattr(request.user, 'perfil'):
        messages.error(request, "No tienes un perfil de usuario asignado.")
        return redirect('/') # O una página de inicio segura

    solicitud_asignada = request.user.perfil.solicitud_actual
    if not solicitud_asignada:
        return render(request, 'creditos/analista_dashboard.html', {'solicitud': None})

    # 2. Lógica de POST: Procesamiento de los diferentes formularios
    if request.method == 'POST':
        # Instanciamos los formularios con los datos del POST
        form_documento = DocumentoAnalisisForm(request.POST, request.FILES)
        form_observacion = ObservacionAnalisisForm(request.POST, instance=solicitud_asignada)
        form_riesgo = AnalisisRiesgoForm(request.POST, instance=solicitud_asignada)

        if 'submit_documento' in request.POST:
            if form_documento.is_valid():
                doc = form_documento.save(commit=False)
                doc.solicitud = solicitud_asignada
                doc.subido_por = request.user
                doc.save()
                messages.success(request, f"Documento '{doc.get_nombre_documento_display()}' cargado.")
            return redirect('analista_dashboard')

        elif 'submit_observacion' in request.POST:
            if form_observacion.is_valid():
                form_observacion.save()
                messages.success(request, "Observación guardada.")
            return redirect('analista_dashboard')

        elif 'submit_riesgo' in request.POST:
            if form_riesgo.is_valid():
                form_riesgo.save()
                aprobado, recomendacion_texto = ejecutar_motor_recomendacion(form_riesgo.cleaned_data)
                solicitud_asignada.recomendacion_sistema_aprobada = aprobado
                solicitud_asignada.recomendacion_sistema_texto = recomendacion_texto
                solicitud_asignada.save()
                messages.info(request, "Recomendación del sistema generada y guardada.")
            else:
                messages.error(request, "Error al generar la recomendación. Por favor, revise los campos.")
            # NO redirigimos, para mostrar el resultado inmediatamente
    
    # 3. Lógica de GET y preparación del contexto final para renderizar
    # Se ejecuta en peticiones GET o después de un POST que no redirige
    
    # Preparamos los formularios (o los volvemos a crear si es una petición GET)
    form_documento = DocumentoAnalisisForm()
    form_observacion = ObservacionAnalisisForm(instance=solicitud_asignada)
    form_riesgo = AnalisisRiesgoForm(instance=solicitud_asignada)
    
    # Preparamos el resto del contexto
    documentos_del_asesor = solicitud_asignada.documentos.filter(subido_por=solicitud_asignada.asesor_comercial)
    documentos_del_analista = solicitud_asignada.documentos.filter(subido_por=request.user)

    # Adjuntamos una instancia del formulario de rechazo a cada documento del asesor
    for doc in documentos_del_asesor:
        doc.rechazo_form = RechazoDocumentoForm(instance=doc)

    docs_obligatorios = {'HISTORIAL_CREDITO', 'PROCESOS_JUDICIALES'}
    docs_cargados_analista = {doc.nombre_documento for doc in documentos_del_analista}


    necesita_correccion = any(
        not doc.ok_analista and doc.observacion_correccion
        for doc in documentos_del_asesor
    )
    
    contexto = {
        'solicitud': solicitud_asignada,
        'form_documento': form_documento,
        'form_observacion': form_observacion,
        'form_riesgo': form_riesgo,
        'documentos_del_asesor': documentos_del_asesor,
        'documentos_del_analista': documentos_del_analista,
        'documentos_obligatorios_ok': docs_obligatorios.issubset(docs_cargados_analista),
        'necesita_correccion': necesita_correccion,
        'recomendacion': solicitud_asignada.recomendacion_sistema_texto,
        'recomendacion_aprobada': solicitud_asignada.recomendacion_sistema_aprobada
    }


    if request.method == 'POST' and 'submit_riesgo' in request.POST:
        form_riesgo_post = AnalisisRiesgoForm(request.POST, instance=solicitud_asignada)
        if form_riesgo_post.is_valid():
            form_riesgo_post.save()
            aprobado, recomendacion_texto = ejecutar_motor_recomendacion(form_riesgo_post.cleaned_data)
            contexto['recomendacion'] = recomendacion_texto
            contexto['recomendacion_aprobada'] = aprobado
        contexto['form_riesgo'] = form_riesgo_post
    
    # 4. Devolvemos la respuesta final
    return render(request, 'creditos/analista_dashboard.html', contexto)



@login_required
def preaprobar_solicitud_view(request, solicitud_id):
    solicitud = get_object_or_404(SolicitudCredito, id=solicitud_id, analista_asignado=request.user)
    if not solicitud.monto_aprobado_calculado:
        messages.error(request, "No se puede continuar. Primero debe guardar una oferta definitiva.")
        return redirect('capacidad_pago', solicitud_id=solicitud.id)
        
    estado_anterior = solicitud.estado
    solicitud.estado = SolicitudCredito.ESTADO_PREAPROBADO
    solicitud.save()
    HistorialEstado.objects.create(
        solicitud=solicitud,
        estado_anterior=estado_anterior,
        estado_nuevo=solicitud.estado,
        usuario_responsable=request.user,
        observaciones="Analista pre-aprobó la solicitud y definió la oferta."
    )
    messages.success(request, f"Solicitud #{solicitud_id} ha sido PRE-APROBADA y ha pasado a la siguiente etapa.")
    return redirect('capacidad_pago', solicitud_id=solicitud.id)



@login_required
def rechazar_solicitud_view(request, solicitud_id):
    solicitud = get_object_or_404(SolicitudCredito, id=solicitud_id, analista_asignado=request.user)
    estado_anterior = solicitud.estado
    solicitud.estado = SolicitudCredito.ESTADO_RECHAZADO_ANALISTA
    solicitud.save()
    HistorialEstado.objects.create(
        solicitud=solicitud,
        estado_anterior=estado_anterior,
        estado_nuevo=solicitud.estado,
        usuario_responsable=request.user,
        observaciones="Analista rechazó la solicitud."
    )
    request.user.perfil.solicitud_actual = None
    request.user.perfil.save()
    messages.warning(request, f"Solicitud #{solicitud.id} ha sido RECHAZADA. Caso cerrado.")
    intentar_asignar_solicitud_en_espera()
    return redirect('analista_dashboard')


@login_required
def capacidad_pago_view(request, solicitud_id):
    solicitud = get_object_or_404(SolicitudCredito, id=solicitud_id, analista_asignado=request.user)

    if solicitud.estado != SolicitudCredito.ESTADO_PREAPROBADO:
        messages.error(request, "Acción no permitida: la solicitud no se encuentra en el estado correcto para este análisis.")
        return redirect('analista_dashboard')
    
    if request.GET.get('action') == 'corregir':
        solicitud.monto_aprobado_calculado = None
        solicitud.plazo_oferta = None
        solicitud.observacion_oferta_final = ""
        solicitud.save()
        messages.info(request, "Oferta borrada. Por favor, ingrese los nuevos valores.")
        return redirect('capacidad_pago', solicitud_id=solicitud.id)
        
    if request.method == 'POST':
        form_capacidad = CapacidadPagoForm(request.POST, instance=solicitud)
        form_oferta_simulacion = OfertaForm(request.POST)
        form_oferta_definitiva = OfertaDefinitivaForm(request.POST, instance=solicitud)

        if 'submit_capacidad' in request.POST:
            if form_capacidad.is_valid():
                instancia_guardada = form_capacidad.save()
                resultado_calculo = calcular_capacidad_pago_service(instancia_guardada)
                capacidad_final = resultado_calculo.get('Capacidad de Pago Mensual (FINAL)', 0)
                if capacidad_final < 0:
                    messages.error(request, f"Cálculo inválido: La capacidad de pago es negativa (${capacidad_final:,.2f}).")
                    instancia_guardada.capacidad_pago_calculada = None
                else:
                    instancia_guardada.capacidad_pago_calculada = capacidad_final
                    messages.success(request, "Cálculo de capacidad de pago realizado y guardado.")
                instancia_guardada.save()
            else:
                messages.error(request, "Error al guardar. Por favor, revise los campos del formulario de análisis.")
            return redirect('capacidad_pago', solicitud_id=solicitud.id)

        elif 'submit_simular_oferta' in request.POST:
            if form_oferta_simulacion.is_valid():
                messages.info(request, "Simulación generada. Ingrese los valores definitivos a continuación.")
            # La vista continuará para re-renderizar la plantilla con los resultados

        elif 'submit_oferta_definitiva' in request.POST:
            if form_oferta_definitiva.is_valid():
                form_oferta_definitiva.save()
                messages.success(request, "¡Oferta definitiva guardada en el sistema!")
            else:
                messages.error(request, "Error al guardar la oferta definitiva. Verifique los valores.")
            return redirect('capacidad_pago', solicitud_id=solicitud.id)
    
    # Lógica de GET y preparación del contexto
    form_capacidad = CapacidadPagoForm(instance=solicitud)
    initial_plazo = solicitud.plazo_oferta if solicitud.plazo_oferta else solicitud.plazo_solicitado
    form_oferta = OfertaForm(instance=solicitud, initial={'plazo_oferta': initial_plazo})
    form_oferta_definitiva = OfertaDefinitivaForm(instance=solicitud)
    
    contexto = {
        'solicitud': solicitud,
        'form_capacidad': form_capacidad,
        'form_oferta': form_oferta,
        'form_oferta_definitiva': form_oferta_definitiva,
        'resultado_capacidad': None,
        'resultado_oferta': None,
    }
    
    if solicitud.capacidad_pago_calculada is not None:
        contexto['resultado_capacidad'] = calcular_capacidad_pago_service(solicitud)
    
    if request.method == 'POST' and 'submit_simular_oferta' in request.POST and form_oferta_simulacion.is_valid():
        solicitud_temporal = solicitud
        solicitud_temporal.plazo_oferta = form_oferta_simulacion.cleaned_data['plazo_oferta']
        contexto['resultado_oferta'] = calcular_oferta_service(solicitud_temporal)
        initial_data = {
            'monto_aprobado_calculado': contexto['resultado_oferta'].get('Monto Máximo a Prestar'),
            'plazo_oferta': contexto['resultado_oferta'].get('Plazo')
        }
        contexto['form_oferta_definitiva'] = OfertaDefinitivaForm(initial=initial_data)

    return render(request, 'creditos/capacidad_pago.html', contexto)




@login_required
def validar_documento_view(request, documento_id):
    documento = get_object_or_404(Documento, id=documento_id)
    solicitud = documento.solicitud
    
    if request.user != solicitud.analista_asignado:
        messages.error(request, "Acción no permitida.")
        return redirect('analista_dashboard')

    if request.method == 'POST':
        if 'aprobar' in request.POST:
            documento.ok_analista = True
            documento.observacion_correccion = ""
            documento.save()
            messages.success(request, f"Documento '{documento.get_nombre_documento_display()}' marcado como CORRECTO.")
        
        elif 'rechazar' in request.POST:
            form = RechazoDocumentoForm(request.POST, instance=documento)
            if form.is_valid() and form.cleaned_data.get('observacion_correccion'):
                documento.ok_analista = False
                form.save()
                messages.warning(request, f"Documento '{documento.get_nombre_documento_display()}' marcado para CORRECCIÓN.")
            else:
                messages.error(request, "Debe especificar un motivo para la corrección.")

    return redirect('analista_dashboard')


@login_required
def devolver_a_asesor_view(request, solicitud_id):
    if request.method == 'POST':
        solicitud = get_object_or_404(SolicitudCredito, id=solicitud_id, analista_asignado=request.user)
        
        estado_anterior = solicitud.estado
        solicitud.estado = SolicitudCredito.ESTADO_DOCS_CORRECCION
        solicitud.save()

        HistorialEstado.objects.create(
            solicitud=solicitud,
            estado_anterior=estado_anterior,
            estado_nuevo=solicitud.estado,
            usuario_responsable=request.user,
            observaciones="Analista devolvió el caso al asesor para corregir documentos."
        )

        request.user.perfil.solicitud_actual = None
        request.user.perfil.save()
        
        intentar_asignar_solicitud_en_espera()

        messages.info(request, f"La solicitud #{solicitud.id} ha sido devuelta al asesor.")
    
    return redirect('analista_dashboard')



@login_required
def corregir_documento_view(request, documento_id):
    if request.method == 'POST':
        documento = get_object_or_404(Documento, id=documento_id)
        solicitud_id = documento.solicitud.id
        
        # Seguridad: solo el asesor de la solicitud puede borrar el documento
        if request.user != documento.solicitud.asesor_comercial:
            messages.error(request, "Acción no permitida.")
            return redirect('listar_solicitudes')
            
        nombre_doc = documento.get_nombre_documento_display()
        documento.delete()
        messages.info(request, f"Documento '{nombre_doc}' eliminado. Por favor, vuelva a subir la versión correcta.")
        return redirect('solicitud_detalle', solicitud_id=solicitud_id)

    # Si no es POST, simplemente redirigir
    return redirect('listar_solicitudes')
