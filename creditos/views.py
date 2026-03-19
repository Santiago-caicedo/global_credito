# En tu archivo: creditos/views.py

from django.http import Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import AuthenticationForm
from usuarios.models import PerfilUsuario
from django.core.paginator import Paginator
from decimal import Decimal
from django.db.models import Count, Sum, Q
from django.db.models.functions import TruncMonth
from .decorators import analista_required, director_required
import json
from .models import ParametrosGlobales, SolicitudCredito, Documento, HistorialEstado, NotificacionEmail, ConsultaDataCredito
from .forms import (
    AnalistaHistorialFiltroForm, CrearUsuarioForm, DocumentoFinalForm, HistorialFiltroForm,
    ObservacionAnalisisForm, ObservacionReferenciasForm, ParametrosGlobalesForm,
    RechazoDocumentoForm, ReferenciaForm, DocumentoForm, DocumentoAnalisisForm,
    AnalisisRiesgoForm, CapacidadPagoForm, OfertaForm, OfertaDefinitivaForm
)
from .services import (
    ejecutar_motor_inicial, asignar_solicitud_a_analista,
    ejecutar_motor_recomendacion, calcular_capacidad_pago_service,
    calcular_oferta_service, intentar_asignar_solicitud_en_espera
)


# ==============================================================================
# VISTAS DEL ANALISTA
# ==============================================================================

@login_required
@analista_required
def analista_caso_activo_view(request):
    if not hasattr(request.user, 'perfil'):
        messages.error(request, "No tienes un perfil de usuario asignado."); return redirect('analista_escritorio')
    
    solicitud_asignada = request.user.perfil.solicitud_actual
    if not solicitud_asignada:
        messages.info(request, "No tiene casos asignados actualmente."); return redirect('analista_escritorio')
    
    if solicitud_asignada.estado != SolicitudCredito.ESTADO_EN_ANALISIS:
        messages.warning(request, f"La solicitud #{solicitud_asignada.id} ya no está en la etapa de análisis de riesgo.")
        # Lo redirigimos a su escritorio para que vea el estado actualizado.
        return redirect('analista_escritorio')
    
    if request.method == 'POST':
        if 'submit_documento' in request.POST:
            form = DocumentoAnalisisForm(request.POST, request.FILES);
            if form.is_valid():
                doc = form.save(commit=False); doc.solicitud = solicitud_asignada; doc.subido_por = request.user; doc.save()
                messages.success(request, f"Documento '{doc.get_nombre_documento_display()}' cargado.")
            return redirect('analista_caso_activo')
        elif 'submit_observacion' in request.POST:
            form = ObservacionAnalisisForm(request.POST, instance=solicitud_asignada)
            if form.is_valid(): form.save(); messages.success(request, "Observación guardada.")
            return redirect('analista_caso_activo')
        elif 'submit_riesgo' in request.POST:
            form_riesgo_post = AnalisisRiesgoForm(request.POST, instance=solicitud_asignada)
            if form_riesgo_post.is_valid():
                form_riesgo_post.save()
                aprobado, recomendacion_texto = ejecutar_motor_recomendacion(form_riesgo_post.cleaned_data)
                solicitud_asignada.recomendacion_sistema_aprobada = aprobado; solicitud_asignada.recomendacion_sistema_texto = recomendacion_texto; solicitud_asignada.save()
                messages.info(request, "Recomendación del sistema generada y guardada.")
    documentos_del_aspirante = solicitud_asignada.documentos.filter(subido_por=solicitud_asignada.aspirante)
    documentos_del_analista = solicitud_asignada.documentos.filter(subido_por=request.user)
    for doc in documentos_del_aspirante: doc.rechazo_form = RechazoDocumentoForm(instance=doc)
    necesita_correccion = any(not doc.ok_analista and doc.observacion_correccion for doc in documentos_del_aspirante)
    docs_obligatorios = {'HISTORIAL_CREDITO', 'PROCESOS_JUDICIALES'}
    docs_cargados_analista = {doc.nombre_documento for doc in documentos_del_analista}
    documentos_obligatorios_ok = docs_obligatorios.issubset(docs_cargados_analista)
    active_step = 1
    if documentos_obligatorios_ok and not necesita_correccion: active_step = 2
    if solicitud_asignada.recomendacion_sistema_texto: active_step = 3
    consulta_hpn = solicitud_asignada.consultas_datacredito.filter(tipo_consulta='HPN').order_by('-fecha_consulta').first()
    consulta_reconocer = solicitud_asignada.consultas_datacredito.filter(tipo_consulta='RECONOCER').order_by('-fecha_consulta').first()

    contexto = {
        'solicitud': solicitud_asignada, 'form_documento': DocumentoAnalisisForm(),
        'form_observacion': ObservacionAnalisisForm(instance=solicitud_asignada),
        'form_riesgo': AnalisisRiesgoForm(instance=solicitud_asignada),
        'documentos_del_aspirante': documentos_del_aspirante, 'documentos_del_analista': documentos_del_analista,
        'documentos_obligatorios_ok': documentos_obligatorios_ok, 'necesita_correccion': necesita_correccion,
        'active_step': active_step,
        'consulta_hpn': consulta_hpn,
        'consulta_reconocer': consulta_reconocer,
    }
    return render(request, 'creditos/analista_caso_activo.html', contexto)



@login_required
@analista_required
def preaprobar_solicitud_view(request, solicitud_id):
    solicitud = get_object_or_404(SolicitudCredito, id=solicitud_id, analista_asignado=request.user)
    
    # 1. Eliminar la validación incorrecta.
    #    La única responsabilidad de esta vista es cambiar el estado y redirigir.
    
    # 2. Actualizar estado y registrar en historial
    estado_anterior = solicitud.estado
    solicitud.estado = SolicitudCredito.ESTADO_PREAPROBADO
    solicitud.save()
    
    HistorialEstado.objects.create(
        solicitud=solicitud,
        estado_anterior=estado_anterior,
        estado_nuevo=solicitud.estado,
        usuario_responsable=request.user,
        observaciones="Analista pre-aprobó la solicitud. Pasando a análisis de capacidad de pago."
    )
    
    # 3. Mostramos un mensaje informativo al analista
    messages.info(request, f"Solicitud #{solicitud.id} pre-aprobada. Por favor, complete el siguiente análisis.")
    
    # 4. Redirigimos a la página de capacidad de pago
    return redirect('capacidad_pago', solicitud_id=solicitud.id)



@login_required
@analista_required
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
    return redirect('analista_escritorio')


@login_required
@analista_required
def capacidad_pago_view(request, solicitud_id):
    solicitud = get_object_or_404(SolicitudCredito, id=solicitud_id, analista_asignado=request.user)
    
    # 1. Seguridad de Estado: Solo se accede si la solicitud está PREAPROBADA
    if solicitud.estado != SolicitudCredito.ESTADO_PREAPROBADO:
        messages.error(request, "Acción no permitida: la solicitud no está en el estado correcto para este análisis.")
        return redirect('analista_escritorio')
    
    # 2. Acción para Corregir Oferta (manejada al principio)
    if request.GET.get('action') == 'corregir':
        solicitud.monto_aprobado_calculado = None
        solicitud.plazo_oferta = None
        solicitud.observacion_oferta_final = ""
        solicitud.save()
        messages.info(request, "Oferta borrada. Por favor, ingrese los nuevos valores.")
        return redirect('capacidad_pago', solicitud_id=solicitud.id)
    
    # 3. Procesamiento de Formularios si la petición es POST
    if request.method == 'POST':
        # --- Formulario 1: Guardar datos de capacidad de pago ---
        if 'submit_capacidad' in request.POST:
            form_capacidad = CapacidadPagoForm(request.POST, instance=solicitud)
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
                return redirect('capacidad_pago', solicitud_id=solicitud.id)
            else:
                # Si el form no es válido, se mostrará con errores
                messages.error(request, "Error al guardar. Por favor, revise los campos del formulario de análisis.")
        
        # --- Formulario 2: Simular oferta de crédito (NO GUARDA NADA) ---
        elif 'submit_simular_oferta' in request.POST:
            form_oferta = OfertaForm(request.POST) # Se procesa el form de simulación
            if form_oferta.is_valid():
                messages.info(request, "Simulación generada. Ingrese los valores definitivos a continuación.")
            # La vista continuará y renderizará la plantilla con los resultados y errores si los hay
        
        # --- Formulario 3: Guardar la oferta definitiva ---
        elif 'submit_oferta_definitiva' in request.POST:
            form_oferta_definitiva = OfertaDefinitivaForm(request.POST, instance=solicitud)
            if form_oferta_definitiva.is_valid():
                form_oferta_definitiva.save()
                messages.success(request, "¡Oferta definitiva guardada en el sistema!")
            else:
                messages.error(request, "Error al guardar la oferta definitiva. Verifique los valores.")
            return redirect('capacidad_pago', solicitud_id=solicitud.id)
        
        # --- Formulario 4: Añadir Referencias ---
        elif 'submit_referencia' in request.POST:
            form_referencia = ReferenciaForm(request.POST)
            if form_referencia.is_valid():
                nueva_referencia = form_referencia.save(commit=False)
                nueva_referencia.solicitud = solicitud
                nueva_referencia.save()
                messages.success(request, "Referencia añadida correctamente.")
            else:
                messages.error(request, "Error al añadir la referencia. Revise los campos.")
            return redirect('capacidad_pago', solicitud_id=solicitud.id)
        
        elif 'submit_observacion_referencias' in request.POST:
            form_obs_ref = ObservacionReferenciasForm(request.POST, instance=solicitud)
            if form_obs_ref.is_valid():
                form_obs_ref.save()
                messages.success(request, "Observación de referencias guardada correctamente.")
            else:
                messages.error(request, "No se pudo guardar la observación.")
            return redirect('capacidad_pago', solicitud_id=solicitud.id)

    # 4. Lógica de GET y preparación del contexto final para renderizar
    # Si no es POST o si un formulario POST no fue válido, se preparan los formularios aquí.
    form_capacidad = CapacidadPagoForm(instance=solicitud)
    initial_plazo = solicitud.plazo_oferta if solicitud.plazo_oferta else solicitud.plazo_solicitado
    form_oferta = OfertaForm(instance=solicitud, initial={'plazo_oferta': initial_plazo})
    form_oferta_definitiva = OfertaDefinitivaForm(instance=solicitud)
    form_referencia = ReferenciaForm()
    form_observaciones_ref = ObservacionReferenciasForm(instance=solicitud)

    contexto = {
        'solicitud': solicitud,
        'form_capacidad': form_capacidad,
        'form_oferta': form_oferta,
        'form_oferta_definitiva': form_oferta_definitiva,
        'form_referencia': form_referencia,
        'form_observaciones_ref': form_observaciones_ref,
        'resultado_capacidad': None,
        'resultado_oferta': None,
    }

    # Se rellenan los resultados si ya existen datos guardados
    if solicitud.capacidad_pago_calculada is not None:
        contexto['resultado_capacidad'] = calcular_capacidad_pago_service(solicitud)
    
    # Lógica para mostrar la simulación después de un POST de simulación
    if request.method == 'POST' and 'submit_simular_oferta' in request.POST:
        form_oferta_simulacion = OfertaForm(request.POST) # Se re-valida para obtener cleaned_data
        if form_oferta_simulacion.is_valid():
            solicitud_temporal = solicitud
            solicitud_temporal.plazo_oferta = form_oferta_simulacion.cleaned_data['plazo_oferta']
            contexto['resultado_oferta'] = calcular_oferta_service(solicitud_temporal)
            
            # Se pre-llena el formulario definitivo con los datos de la simulación
            initial_data = {
                'monto_aprobado_calculado': contexto['resultado_oferta'].get('Monto Máximo a Prestar'),
                'plazo_oferta': contexto['resultado_oferta'].get('Plazo')
            }
            contexto['form_oferta_definitiva'] = OfertaDefinitivaForm(initial=initial_data)
        else:
             contexto['form_oferta'] = form_oferta_simulacion # Pasamos el form con errores para que se muestren
             
    return render(request, 'creditos/capacidad_pago.html', contexto)





@login_required
@analista_required
def validar_documento_view(request, documento_id):
    documento = get_object_or_404(Documento, id=documento_id)
    solicitud = documento.solicitud
    
    if request.user != solicitud.analista_asignado:
        messages.error(request, "Acción no permitida.")
        redirect('analista_caso_activo')

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

    estados_validacion_final = [
        SolicitudCredito.ESTADO_EN_VALIDACION_DOCS,
        SolicitudCredito.ESTADO_DOCS_FINALES_CORRECCION
    ]
    if solicitud.estado in estados_validacion_final:
        return redirect('validacion_final', solicitud_id=solicitud.id)
    else:
        # Si no, es una validación inicial, volvemos al caso activo.
        return redirect('analista_caso_activo')


@login_required
@analista_required
def devolver_a_aspirante_view(request, solicitud_id):
    """Devuelve la solicitud al aspirante para que corrija documentos."""
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
            observaciones="Analista devolvió el caso al aspirante para corregir documentos."
        )

        # Enviar notificación por email al aspirante
        from .models import NotificacionEmail
        from .services import enviar_notificacion_email
        site_url = request.build_absolute_uri('/').rstrip('/')
        enviar_notificacion_email(solicitud, NotificacionEmail.TIPO_DOCUMENTOS_RECHAZADOS, extra_context={'site_url': site_url})

        request.user.perfil.solicitud_actual = None
        request.user.perfil.save()

        intentar_asignar_solicitud_en_espera()

        messages.info(request, f"La solicitud #{solicitud.id} ha sido devuelta al aspirante.")
    
    return redirect('analista_escritorio')





def enviar_para_documentos_finales_view(request, solicitud_id):
    """
    Esta vista se activa cuando el analista da su aprobación final
    y envía el caso al aspirante para que cargue los documentos de cierre.
    """
    if request.method == 'POST':
        solicitud = get_object_or_404(SolicitudCredito, id=solicitud_id, analista_asignado=request.user)

        # Validación: Asegurarse de que una oferta definitiva esté guardada
        if not solicitud.monto_aprobado_calculado or not solicitud.plazo_oferta:
            messages.error(request, "No se puede continuar. Primero debe guardar una oferta definitiva.")
            return redirect('capacidad_pago', solicitud_id=solicitud.id)

        estado_anterior = solicitud.estado
        solicitud.estado = SolicitudCredito.ESTADO_PEND_DOCS_ADICIONALES
        solicitud.save()

        HistorialEstado.objects.create(
            solicitud=solicitud,
            estado_anterior=estado_anterior,
            estado_nuevo=solicitud.estado,
            usuario_responsable=request.user,
            observaciones="Analista aprobó la oferta. Solicitando documentos finales al aspirante."
        )

        # Enviar notificación por email al aspirante
        from .services import enviar_notificacion_email
        site_url = request.build_absolute_uri('/').rstrip('/')
        enviar_notificacion_email(solicitud, NotificacionEmail.TIPO_CAMBIO_ESTADO, extra_context={'site_url': site_url})

        # El analista aún no se libera. Queda "dueño" del caso.
        messages.success(request, f"Solicitud #{solicitud.id} aprobada. Se ha notificado al aspirante para que cargue los documentos finales.")
        
        # Lo redirigimos a su dashboard principal
        return redirect('analista_escritorio')

    return redirect('analista_escritorio')






@login_required
@analista_required
def validacion_final_view(request, solicitud_id):
    solicitud = get_object_or_404(SolicitudCredito, id=solicitud_id, analista_asignado=request.user)
    
    estados_permitidos = [
        SolicitudCredito.ESTADO_EN_VALIDACION_DOCS,
        SolicitudCredito.ESTADO_DOCS_FINALES_CORRECCION # Permitimos acceso si está en corrección
    ]
    if solicitud.estado not in estados_permitidos:
        messages.error(request, "La solicitud no se encuentra en la etapa de validación final.")
        return redirect('analista_escritorio')

    tipos_documento_cierre = ['PAGARE', 'CARTA_INSTRUCCIONES', 'POLIZA_SEGURO', 'FORMATO_VINCULACION']
    documentos_finales = solicitud.documentos.filter(nombre_documento__in=tipos_documento_cierre)
    
    for doc in documentos_finales:
        doc.rechazo_form = RechazoDocumentoForm(instance=doc)
        
    # Lógica de comprobación
    necesita_correccion_final = any(not doc.ok_analista and doc.observacion_correccion for doc in documentos_finales)
    todos_ok = all(doc.ok_analista for doc in documentos_finales) if documentos_finales else False

    contexto = {
        'solicitud': solicitud,
        'documentos_finales': documentos_finales,
        'todos_documentos_ok': todos_ok,
        'necesita_correccion_final': necesita_correccion_final,
    }
    return render(request, 'creditos/validacion_final.html', contexto)




@login_required
@analista_required
def analista_escritorio_view(request):
    """
    El nuevo escritorio del analista, con estadísticas y un diseño profesional.
    """
    solicitud_actual = None
    if hasattr(request.user, 'perfil'):
        solicitud_actual = request.user.perfil.solicitud_actual
        
    # --- LÓGICA AÑADIDA PARA LAS ESTADÍSTICAS ---
    # Estados que consideramos "finalizados" desde la perspectiva del analista
    estados_finalizados = [
        SolicitudCredito.ESTADO_RECHAZADO_ANALISTA,
        SolicitudCredito.ESTADO_APROBADO,
        SolicitudCredito.ESTADO_DESEMBOLSADO,
        SolicitudCredito.ESTADO_RECHAZADO_DIRECTOR,
    ]
    
    # Contamos cuántas solicitudes ha atendido el analista
    solicitudes_atendidas_count = SolicitudCredito.objects.filter(
        analista_asignado=request.user,
        estado__in=estados_finalizados
    ).count()

    # Obtenemos las últimas 5 solicitudes atendidas para la tabla de historial rápido
    ultimas_solicitudes_atendidas = SolicitudCredito.objects.filter(
        analista_asignado=request.user,
        estado__in=estados_finalizados
    ).order_by('-fecha_actualizacion')[:5]
    # ------------------------------------------------

    contexto = {
        'solicitud_actual': solicitud_actual,
        'solicitudes_atendidas_count': solicitudes_atendidas_count,
        'ultimas_solicitudes': ultimas_solicitudes_atendidas,
    }
    return render(request, 'creditos/analista_escritorio.html', contexto)




@login_required
@analista_required
def historial_analista_view(request):
    """
    Muestra el historial de solicitudes atendidas por el analista,
    con filtros y paginación.
    """
    estados_finalizados = [
        SolicitudCredito.ESTADO_RECHAZADO_ANALISTA,
        SolicitudCredito.ESTADO_APROBADO,
        SolicitudCredito.ESTADO_RECHAZADO_DIRECTOR,
        SolicitudCredito.ESTADO_PEND_APROB_DIRECTOR # Incluimos los que envió al director
    ]
    
    # Obtenemos la base de solicitudes del analista
    solicitudes_list = SolicitudCredito.objects.filter(
        analista_asignado=request.user,
        estado__in=estados_finalizados
    ).order_by('-fecha_actualizacion')

    # Aplicamos los filtros si se enviaron en la URL
    form = AnalistaHistorialFiltroForm(request.GET)
    if form.is_valid():
        if form.cleaned_data.get('estado'):
            solicitudes_list = solicitudes_list.filter(estado=form.cleaned_data['estado'])
        if form.cleaned_data.get('fecha_inicio'):
            solicitudes_list = solicitudes_list.filter(fecha_actualizacion__gte=form.cleaned_data['fecha_inicio'])
        if form.cleaned_data.get('fecha_fin'):
            solicitudes_list = solicitudes_list.filter(fecha_actualizacion__lte=form.cleaned_data['fecha_fin'])

    # Paginación: mostramos 15 solicitudes por página
    paginator = Paginator(solicitudes_list, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    contexto = {
        'page_obj': page_obj,
        'form': form,
    }
    return render(request, 'creditos/historial_analista.html', contexto)





@login_required
@analista_required
def enviar_a_director_view(request, solicitud_id):
    """
    Acción final del analista. Cambia el estado, libera al analista
    y envía la solicitud a la última etapa de aprobación.
    """
    if request.method == 'POST':
        solicitud = get_object_or_404(SolicitudCredito, id=solicitud_id, analista_asignado=request.user)
        
        # Validación de seguridad: Asegurarse de que todos los documentos estén OK
        tipos_cierre = ['PAGARE', 'CARTA_INSTRUCCIONES', 'POLIZA_SEGURO', 'FORMATO_VINCULACION']
        docs_finales = solicitud.documentos.filter(nombre_documento__in=tipos_cierre)
        if not all(doc.ok_analista for doc in docs_finales):
            messages.error(request, "No se puede enviar. Aún hay documentos pendientes de validación.")
            return redirect('validacion_final', solicitud_id=solicitud.id)

        estado_anterior = solicitud.estado
        solicitud.estado = SolicitudCredito.ESTADO_PEND_APROB_DIRECTOR
        solicitud.save()

        HistorialEstado.objects.create(
            solicitud=solicitud,
            estado_anterior=estado_anterior,
            estado_nuevo=solicitud.estado,
            usuario_responsable=request.user,
            observaciones="Analista validó todos los documentos y envió a aprobación final del Director."
        )

        # Liberamos al analista
        request.user.perfil.solicitud_actual = None
        request.user.perfil.save()
        
        # Intentamos asignar un nuevo caso de la cola
        intentar_asignar_solicitud_en_espera()

        messages.success(request, f"Solicitud #{solicitud.id} enviada correctamente a aprobación del Director.")
        return redirect('analista_escritorio')
    
    return redirect('analista_escritorio')



@login_required
@analista_required
def devolver_docs_finales_view(request, solicitud_id):
    """
    Devuelve el caso al aspirante para corregir DOCUMENTOS FINALES,
    pero MANTIENE la asignación al analista.
    """
    if request.method == 'POST':
        solicitud = get_object_or_404(SolicitudCredito, id=solicitud_id, analista_asignado=request.user)

        estado_anterior = solicitud.estado
        solicitud.estado = SolicitudCredito.ESTADO_DOCS_FINALES_CORRECCION
        solicitud.save()

        HistorialEstado.objects.create(
            solicitud=solicitud,
            estado_anterior=estado_anterior,
            estado_nuevo=solicitud.estado,
            usuario_responsable=request.user,
            observaciones="Analista devolvió caso para corregir documentos finales."
        )

        # Enviar notificación por email al aspirante
        from .services import enviar_notificacion_email
        site_url = request.build_absolute_uri('/').rstrip('/')
        enviar_notificacion_email(solicitud, NotificacionEmail.TIPO_DOCUMENTOS_RECHAZADOS, extra_context={'site_url': site_url})

        messages.info(request, f"La solicitud #{solicitud.id} ha sido devuelta al aspirante para corrección.")
        
        # Redirigimos al escritorio, ya que el analista no puede hacer más hasta que se corrija.
        return redirect('analista_escritorio')
    
    return redirect('analista_escritorio')



@login_required
@analista_required
def analista_detalle_historial_view(request, solicitud_id):
    """
    Muestra a un analista el detalle completo de una solicitud que ya ha procesado.
    Es una vista de solo lectura.
    """
    # Seguridad: Solo el analista que trabajó en el caso puede verlo.
    solicitud = get_object_or_404(SolicitudCredito, id=solicitud_id, analista_asignado=request.user)
    
    # Recopilamos toda la información para mostrarla
    tipos_iniciales = ['CEDULA', 'DECLARACION_RENTA', 'CERTIFICADO_LABORAL', 'AUTORIZACION_CONSULTA']
    tipos_cierre = ['PAGARE', 'CARTA_INSTRUCCIONES', 'POLIZA_SEGURO', 'FORMATO_VINCULACION']

    documentos_iniciales_aspirante = solicitud.documentos.filter(nombre_documento__in=tipos_iniciales)
    documentos_finales_aspirante = solicitud.documentos.filter(nombre_documento__in=tipos_cierre)
    documentos_analista = solicitud.documentos.filter(subido_por=solicitud.analista_asignado)

    # Volvemos a calcular el desglose de capacidad de pago para mostrarlo
    resultado_capacidad = None
    if solicitud.capacidad_pago_calculada is not None:
        resultado_capacidad = calcular_capacidad_pago_service(solicitud)

    contexto = {
        'solicitud': solicitud,
        'documentos_iniciales_aspirante': documentos_iniciales_aspirante,
        'documentos_finales_aspirante': documentos_finales_aspirante,
        'documentos_analista': documentos_analista,
        'referencias': solicitud.referencias.all(),
        'resultado_capacidad': resultado_capacidad,
    }
    return render(request, 'creditos/analista_detalle_historial.html', contexto)


@login_required
@analista_required
def eliminar_documento_analista_view(request, documento_id):
    """
    Permite al analista eliminar un documento que él mismo ha subido.
    """
    if request.method == 'POST':
        documento = get_object_or_404(Documento, id=documento_id)
        
        # Seguridad: solo el analista asignado puede borrar el documento
        if request.user == documento.solicitud.analista_asignado:
            nombre_doc = documento.get_nombre_documento_display()
            documento.delete()
            messages.success(request, f"Documento '{nombre_doc}' eliminado correctamente.")
        else:
            messages.error(request, "Acción no permitida.")
            
    return redirect('analista_caso_activo')


# ==============================================================================
# VISTAS DEL DIRECTOR
# ==============================================================================

@login_required
@director_required
def director_escritorio_view(request):
    """
    Dashboard del Director con indicadores de entrada, tasas,
    tiempos de respuesta y distribución por convenio.
    """
    S = SolicitudCredito  # alias

    # ===== 1. TOTAL SOLICITUDES RECIBIDAS =====
    total_solicitudes = S.objects.count()
    total_monto_solicitado = S.objects.aggregate(
        total=Sum('monto_solicitado')
    )['total'] or 0

    # ===== 2. SOLICITUDES POR CONVENIO =====
    solicitudes_por_convenio = list(
        S.objects.exclude(convenio__isnull=True).exclude(convenio='')
        .values('convenio')
        .annotate(count=Count('id'), monto_total=Sum('monto_solicitado'))
        .order_by('-count')
    )
    sin_convenio_count = S.objects.filter(
        Q(convenio__isnull=True) | Q(convenio='')
    ).count()

    # ===== 3. APROBADOS (incluye desembolsados) =====
    estados_aprobados = [S.ESTADO_APROBADO, S.ESTADO_DESEMBOLSADO]
    aprobados_count = S.objects.filter(estado__in=estados_aprobados).count()
    tasa_aprobacion = (aprobados_count / total_solicitudes * 100) if total_solicitudes > 0 else 0

    # ===== 4. DESEMBOLSOS =====
    desembolsados_count = S.objects.filter(estado=S.ESTADO_DESEMBOLSADO).count()
    tasa_desembolso = (desembolsados_count / total_solicitudes * 100) if total_solicitudes > 0 else 0
    total_monto_desembolsado = S.objects.filter(
        estado=S.ESTADO_DESEMBOLSADO
    ).aggregate(total=Sum('monto_aprobado_calculado'))['total'] or 0

    # ===== 5. TASA DE DESISTIMIENTO =====
    aprobados_sin_desembolso = S.objects.filter(estado=S.ESTADO_APROBADO).count()
    tasa_desistimiento = (aprobados_sin_desembolso / aprobados_count * 100) if aprobados_count > 0 else 0

    # ===== 6. NEGADOS =====
    estados_negados = [
        S.ESTADO_RECHAZADO_AUTO,
        S.ESTADO_RECHAZADO_ANALISTA,
        S.ESTADO_RECHAZADO_DIRECTOR,
    ]
    negados_count = S.objects.filter(estado__in=estados_negados).count()
    tasa_negacion = (negados_count / total_solicitudes * 100) if total_solicitudes > 0 else 0

    # ===== 7. TIEMPOS PROMEDIO DE RESPUESTA =====
    # Radicado → Aprobado
    tiempo_radicado_aprobado_dias = None
    solicitudes_con_aprobacion = S.objects.filter(estado__in=estados_aprobados + [S.ESTADO_DESEMBOLSADO])
    if solicitudes_con_aprobacion.exists():
        tiempos_ra = []
        for sol in solicitudes_con_aprobacion.only('id', 'fecha_creacion'):
            hist = sol.historial.filter(estado_nuevo='APROBADO').order_by('fecha_cambio').first()
            if hist:
                tiempos_ra.append((hist.fecha_cambio - sol.fecha_creacion).total_seconds() / 86400)
        if tiempos_ra:
            tiempo_radicado_aprobado_dias = round(sum(tiempos_ra) / len(tiempos_ra), 1)

    # Aprobado → Desembolsado
    tiempo_aprobado_desembolsado_dias = None
    solicitudes_desembolsadas = S.objects.filter(estado=S.ESTADO_DESEMBOLSADO)
    if solicitudes_desembolsadas.exists():
        tiempos_ad = []
        for sol in solicitudes_desembolsadas.only('id'):
            h_apr = sol.historial.filter(estado_nuevo='APROBADO').order_by('fecha_cambio').first()
            h_des = sol.historial.filter(estado_nuevo='DESEMBOLSADO').order_by('fecha_cambio').first()
            if h_apr and h_des:
                tiempos_ad.append((h_des.fecha_cambio - h_apr.fecha_cambio).total_seconds() / 86400)
        if tiempos_ad:
            tiempo_aprobado_desembolsado_dias = round(sum(tiempos_ad) / len(tiempos_ad), 1)

    # ===== 8. PENDIENTES DE APROBACION =====
    solicitudes_pendientes_count = S.objects.filter(estado=S.ESTADO_PEND_APROB_DIRECTOR).count()

    # ===== 9. GRAFICOS =====
    solicitudes_por_mes = S.objects.annotate(
        month=TruncMonth('fecha_creacion')
    ).values('month').annotate(count=Count('id')).order_by('month')
    labels_line_chart = [s['month'].strftime('%b %Y') for s in solicitudes_por_mes]
    data_line_chart = [s['count'] for s in solicitudes_por_mes]

    estados_finales = [
        S.ESTADO_APROBADO, S.ESTADO_DESEMBOLSADO,
        S.ESTADO_RECHAZADO_DIRECTOR, S.ESTADO_RECHAZADO_ANALISTA, S.ESTADO_RECHAZADO_AUTO
    ]
    distribucion_estados = S.objects.filter(estado__in=estados_finales).values('estado').annotate(count=Count('id'))
    labels_donut_chart = [dict(S.ESTADOS_CHOICES).get(d['estado']) for d in distribucion_estados]
    data_donut_chart = [d['count'] for d in distribucion_estados]

    # ===== 10. ACCIONES INMEDIATAS =====
    ultimas_pendientes = S.objects.filter(
        estado=S.ESTADO_PEND_APROB_DIRECTOR
    ).order_by('fecha_actualizacion')[:5]

    contexto = {
        # Indicadores de entrada
        'total_solicitudes': total_solicitudes,
        'total_monto_solicitado': total_monto_solicitado,
        'solicitudes_por_convenio': solicitudes_por_convenio,
        'sin_convenio_count': sin_convenio_count,
        # Aprobados
        'aprobados_count': aprobados_count,
        'tasa_aprobacion': round(tasa_aprobacion, 1),
        # Desembolsos
        'desembolsados_count': desembolsados_count,
        'tasa_desembolso': round(tasa_desembolso, 1),
        'total_monto_desembolsado': total_monto_desembolsado,
        # Desistimiento
        'aprobados_sin_desembolso': aprobados_sin_desembolso,
        'tasa_desistimiento': round(tasa_desistimiento, 1),
        # Negados
        'negados_count': negados_count,
        'tasa_negacion': round(tasa_negacion, 1),
        # Tiempos
        'tiempo_radicado_aprobado_dias': tiempo_radicado_aprobado_dias,
        'tiempo_aprobado_desembolsado_dias': tiempo_aprobado_desembolsado_dias,
        # Pendientes
        'solicitudes_pendientes_count': solicitudes_pendientes_count,
        # Gráficos
        'labels_line_chart': json.dumps(labels_line_chart),
        'data_line_chart': json.dumps(data_line_chart),
        'labels_donut_chart': json.dumps(labels_donut_chart),
        'data_donut_chart': json.dumps(data_donut_chart),
        # Acciones
        'ultimas_pendientes': ultimas_pendientes,
    }
    return render(request, 'creditos/director_escritorio.html', contexto)



@login_required
@director_required
def gestion_parametros_view(request):
    # Obtenemos la única instancia de parámetros, o creamos una si no existe.
    parametros, created = ParametrosGlobales.objects.get_or_create(pk=1)
    
    if request.method == 'POST':
        form = ParametrosGlobalesForm(request.POST, instance=parametros)
        if form.is_valid():
            form.save()
            messages.success(request, "Los parámetros globales han sido actualizados correctamente.")
            return redirect('gestion_parametros')
    else:
        form = ParametrosGlobalesForm(instance=parametros)

    contexto = {
        'form': form
    }
    return render(request, 'creditos/gestion_parametros.html', contexto)



@login_required
@director_required
def director_pendientes_view(request):
    """
    Muestra al Director una lista de todas las solicitudes que están
    en estado 'Pendiente Aprobación Director'.
    """
    solicitudes_pendientes = SolicitudCredito.objects.filter(
        estado=SolicitudCredito.ESTADO_PEND_APROB_DIRECTOR
    ).order_by('fecha_actualizacion') # Mostramos las más antiguas primero

    contexto = {
        'solicitudes': solicitudes_pendientes
    }
    return render(request, 'creditos/director_pendientes.html', contexto)




@login_required
@director_required
def director_detalle_solicitud_view(request, solicitud_id):
    """
    Muestra al Director el detalle completo, separando los tipos de documentos
    para una revisión más clara.
    """
    solicitud = get_object_or_404(SolicitudCredito, id=solicitud_id)
    

    # 1. Definimos los tipos de documentos para cada categoría
    tipos_iniciales = ['CEDULA', 'DECLARACION_RENTA', 'CERTIFICADO_LABORAL', 'AUTORIZACION_CONSULTA']
    tipos_cierre = ['PAGARE', 'CARTA_INSTRUCCIONES', 'POLIZA_SEGURO', 'FORMATO_VINCULACION']

    # 2. Filtramos cada lista de documentos por separado
    documentos_iniciales_aspirante = solicitud.documentos.filter(
        subido_por=solicitud.aspirante,
        nombre_documento__in=tipos_iniciales
    )
    documentos_finales_aspirante = solicitud.documentos.filter(
        subido_por=solicitud.aspirante,
        nombre_documento__in=tipos_cierre
    )
    documentos_analista = solicitud.documentos.filter(subido_por=solicitud.analista_asignado)

    # 3. Calculamos el desglose de capacidad de pago
    resultado_capacidad = calcular_capacidad_pago_service(solicitud) if solicitud.capacidad_pago_calculada is not None else None

    # 4. Consultas DataCredito
    consulta_hpn = solicitud.consultas_datacredito.filter(tipo_consulta='HPN').order_by('-fecha_consulta').first()
    consulta_reconocer = solicitud.consultas_datacredito.filter(tipo_consulta='RECONOCER').order_by('-fecha_consulta').first()

    # 5. Preparamos el contexto con las listas separadas
    contexto = {
        'solicitud': solicitud,
        'documentos_iniciales_aspirante': documentos_iniciales_aspirante,
        'documentos_finales_aspirante': documentos_finales_aspirante,
        'documentos_analista': documentos_analista,
        'historial': solicitud.historial.all(),
        'referencias': solicitud.referencias.all(),
        'resultado_capacidad': resultado_capacidad,
        'consulta_hpn': consulta_hpn,
        'consulta_reconocer': consulta_reconocer,
    }
    return render(request, 'creditos/director_detalle_solicitud.html', contexto)




@login_required
@director_required
def aprobar_credito_final_view(request, solicitud_id):
    """
    Acción final para APROBAR el crédito. Cambia el estado y cierra el caso.
    """
    if request.method == 'POST':
        solicitud = get_object_or_404(SolicitudCredito, id=solicitud_id)
        
        estado_anterior = solicitud.estado
        solicitud.estado = SolicitudCredito.ESTADO_APROBADO
        solicitud.save()

        HistorialEstado.objects.create(
            solicitud=solicitud,
            estado_anterior=estado_anterior,
            estado_nuevo=solicitud.estado,
            usuario_responsable=request.user,
            observaciones="Director aprobó el crédito definitivamente."
        )
        
        messages.success(request, f"¡Éxito! La Solicitud #{solicitud.id} ha sido APROBADA y el proceso ha finalizado.")
        return redirect('director_pendientes')
    
    return redirect('director_pendientes')


@login_required
@director_required
def rechazar_credito_final_view(request, solicitud_id):
    """
    Acción final para RECHAZAR el crédito. Cambia el estado y cierra el caso.
    """
    if request.method == 'POST':
        solicitud = get_object_or_404(SolicitudCredito, id=solicitud_id)

        estado_anterior = solicitud.estado
        solicitud.estado = SolicitudCredito.ESTADO_RECHAZADO_DIRECTOR
        solicitud.save()

        HistorialEstado.objects.create(
            solicitud=solicitud,
            estado_anterior=estado_anterior,
            estado_nuevo=solicitud.estado,
            usuario_responsable=request.user,
            observaciones="Director rechazó el crédito definitivamente."
        )

        messages.warning(request, f"La Solicitud #{solicitud.id} ha sido RECHAZADA y el proceso ha finalizado.")
        return redirect('director_pendientes')

    return redirect('director_pendientes')


@login_required
@director_required
def desembolsar_credito_view(request, solicitud_id):
    """
    Registra el desembolso de un crédito aprobado.
    """
    if request.method == 'POST':
        solicitud = get_object_or_404(SolicitudCredito, id=solicitud_id)

        if solicitud.estado != SolicitudCredito.ESTADO_APROBADO:
            messages.error(request, "Solo se pueden desembolsar créditos aprobados.")
            return redirect('director_escritorio')

        estado_anterior = solicitud.estado
        solicitud.estado = SolicitudCredito.ESTADO_DESEMBOLSADO
        solicitud.save()

        HistorialEstado.objects.create(
            solicitud=solicitud,
            estado_anterior=estado_anterior,
            estado_nuevo=solicitud.estado,
            usuario_responsable=request.user,
            observaciones="Director registró el desembolso del crédito."
        )

        messages.success(request, f"Solicitud #{solicitud.id} marcada como DESEMBOLSADA exitosamente.")
        return redirect('director_escritorio')

    return redirect('director_escritorio')




@login_required
@director_required
def historial_completo_view(request):
    """
    Muestra el historial completo de todas las solicitudes con filtros
    y paginación.
    """
    # Empezamos con todas las solicitudes
    solicitudes_list = SolicitudCredito.objects.all().order_by('-fecha_creacion')
    
    # Creamos una instancia del formulario, pasándole los datos de la URL si existen (GET)
    form = HistorialFiltroForm(request.GET)
    
    # Aplicamos los filtros si el formulario es válido
    if form.is_valid():
        if form.cleaned_data.get('estado'):
            solicitudes_list = solicitudes_list.filter(estado=form.cleaned_data['estado'])
        if form.cleaned_data.get('analista'):
            solicitudes_list = solicitudes_list.filter(analista_asignado=form.cleaned_data['analista'])
        if form.cleaned_data.get('fecha_inicio'):
            solicitudes_list = solicitudes_list.filter(fecha_creacion__gte=form.cleaned_data['fecha_inicio'])
        if form.cleaned_data.get('fecha_fin'):
            solicitudes_list = solicitudes_list.filter(fecha_creacion__lte=form.cleaned_data['fecha_fin'])

    # Paginación: mostramos 20 solicitudes por página
    paginator = Paginator(solicitudes_list, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    contexto = {
        'page_obj': page_obj, # Enviamos el objeto de la página a la plantilla
        'form': form,
    }
    return render(request, 'creditos/historial_completo.html', contexto)





#vista para gestionar usuarios desde perfil de director

@login_required
@director_required
def gestion_usuarios_view(request):
    """Página principal de Gestión de Usuarios (solo Analistas)."""
    return render(request, 'creditos/gestion_usuarios.html')

@login_required
@director_required
def gestion_rol_view(request, rol):
    """Página intermedia que ofrece las opciones de 'Ver' o 'Añadir' para un rol específico."""
    rol_mayuscula = rol.upper()
    if rol_mayuscula != 'ANALISTA':
        raise Http404("Rol no válido")

    contexto = {
        'rol': rol,
        'rol_display': 'Analistas'
    }
    return render(request, 'creditos/gestion_rol.html', contexto)

@login_required
@director_required
def listar_usuarios_por_rol_view(request, rol):
    """Muestra una lista de todos los usuarios para un rol específico."""
    rol_mayuscula = rol.upper()
    if rol_mayuscula != 'ANALISTA':
        raise Http404("Rol no válido")

    usuarios = User.objects.filter(perfil__rol=rol_mayuscula).order_by('username')
    contexto = {
        'rol': rol,
        'rol_display': 'Analistas',
        'usuarios': usuarios
    }
    return render(request, 'creditos/listar_usuarios.html', contexto)

@login_required
@director_required
def crear_usuario_rol_view(request, rol):
    rol_mayuscula = rol.upper()
    if rol_mayuscula != 'ANALISTA':
        raise Http404("Rol no válido")

    if request.method == 'POST':
        form = CrearUsuarioForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            if User.objects.filter(username=username).exists():
                messages.error(request, f"El nombre de usuario '{username}' ya existe.")
            else:
                # Creamos el usuario de Django
                new_user = User.objects.create_user(
                    username=form.cleaned_data['username'],
                    password=form.cleaned_data['password'],
                    email=form.cleaned_data['email'],
                    first_name=form.cleaned_data['first_name'],
                    last_name=form.cleaned_data['last_name'],
                    is_staff=True
                )
                # Creamos el perfil
                PerfilUsuario.objects.create(
                    usuario=new_user,
                    rol=rol_mayuscula,
                    telefono=form.cleaned_data.get('telefono')
                )
                messages.success(request, f"Usuario '{username}' creado exitosamente.")
                return redirect('listar_usuarios', rol=rol)
    else:
        form = CrearUsuarioForm()

    contexto = {
        'form': form,
        'rol': rol,
        'rol_display': 'Analista'
    }
    return render(request, 'creditos/crear_usuario.html', contexto)
@login_required
@director_required
def eliminar_usuario_view(request, usuario_id):
    """Procesa la eliminación de un usuario."""
    if request.method == 'POST':
        usuario_a_eliminar = get_object_or_404(User, id=usuario_id)
        rol = usuario_a_eliminar.perfil.rol.lower()
        if usuario_a_eliminar == request.user:
            messages.error(request, "No puede eliminarse a sí mismo.")
        else:
            username = usuario_a_eliminar.username
            usuario_a_eliminar.delete()
            messages.warning(request, f"Usuario '{username}' eliminado permanentemente.")
        return redirect('listar_usuarios', rol=rol)
    return redirect('gestion_usuarios')
