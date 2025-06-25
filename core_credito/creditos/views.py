from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import SolicitudCreditoForm,  DocumentoForm, ObservacionesAnalistaForm, ReferenciaForm
from .forms import DocumentoAnalisisForm, ObservacionAnalisisForm, AnalisisRiesgoForm, CapacidadPagoForm
from .services import calcular_capacidad_pago_service, ejecutar_motor_inicial, intentar_asignar_solicitud_en_espera
from .models import HistorialEstado, SolicitudCredito, Documento, Referencia
from .services import asignar_solicitud_a_analista, ejecutar_motor_recomendacion

@login_required
def crear_solicitud_view(request):
    if request.method == 'POST':
        form = SolicitudCreditoForm(request.POST)
        if form.is_valid():
            # Creamos el objeto en memoria, pero no lo guardamos aún en la BD
            solicitud = form.save(commit=False)
            
            # Asignamos el asesor logueado actualmente
            solicitud.asesor_comercial = request.user
            
            # Ahora sí, guardamos la solicitud inicial
            solicitud.save()
            HistorialEstado.objects.create(
                solicitud=solicitud,
                estado_nuevo=solicitud.estado,
                usuario_responsable=request.user,
                observaciones="Creación de la solicitud por asesor."
            )
            
            # --- Aquí empieza la magia del backend ---
            # 1. Enriquecer los datos (en el futuro, con APIs reales)
            
            # 2. Ejecutar el motor de decisión
            nuevo_estado, observacion_motor = ejecutar_motor_inicial(solicitud)
            
            # 3. Actualizar el estado de la solicitud con el resultado del motor
            solicitud.estado = nuevo_estado
            solicitud.save()

            # 4. Guardar el resultado en el historial
            HistorialEstado.objects.create(
                solicitud=solicitud,
                estado_anterior=solicitud.ESTADO_NUEVO,
                estado_nuevo=nuevo_estado,
                usuario_responsable=None, # El sistema es el responsable
                observaciones=f"Resultado del motor de decisión: {observacion_motor}"
            )
            
            # TODO: Implementar el envío de correo electrónico al asesor
            
            messages.success(request, f'Solicitud #{solicitud.id} creada. Resultado: {observacion_motor}')
            return redirect('listar_solicitudes') 

    else: # Si el método es GET
        form = SolicitudCreditoForm()
        
    return render(request, 'creditos/crear_solicitud.html', {'form': form})

@login_required
def listar_solicitudes_view(request):
    # Filtramos las solicitudes para obtener SOLO las del usuario que está logueado
    solicitudes_del_asesor = SolicitudCredito.objects.filter(asesor_comercial=request.user)
    
    contexto = {
        'solicitudes': solicitudes_del_asesor
    }
    return render(request, 'creditos/listar_solicitudes.html', contexto)



@login_required
def solicitud_detalle_view(request, solicitud_id):
    solicitud = get_object_or_404(SolicitudCredito, id=solicitud_id)
    # Solo mostramos el formulario si el usuario actual es el asesor de la solicitud
    if request.user == solicitud.asesor_comercial:
        form_documento = DocumentoForm()
    else:
        form_documento = None

    if request.method == 'POST':
        # Asegurarse de que solo el asesor pueda subir documentos aquí
        if request.user != solicitud.asesor_comercial:
            messages.error(request, "No tienes permiso para realizar esta acción.")
            return redirect('solicitud_detalle', solicitud_id=solicitud.id)
            
        form = DocumentoForm(request.POST, request.FILES)
        if form.is_valid():
            nuevo_documento = form.save(commit=False)
            nuevo_documento.solicitud = solicitud
            # --- LÍNEA AÑADIDA (LA CORRECCIÓN) ---
            nuevo_documento.subido_por = request.user
            # ------------------------------------
            nuevo_documento.save()
            messages.success(request, f"Documento '{nuevo_documento.get_nombre_documento_display()}' cargado exitosamente.")
        else:
            messages.error(request, "Error al cargar el documento. Por favor, intente de nuevo.")
        
        return redirect('solicitud_detalle', solicitud_id=solicitud.id)

    contexto = {
        'solicitud': solicitud,
        'form_documento': form_documento
    }
    return render(request, 'creditos/solicitud_detalle.html', contexto)




@login_required
def enviar_a_asignacion_view(request, solicitud_id):
    if request.method == 'POST':
        solicitud = get_object_or_404(SolicitudCredito, id=solicitud_id)

        # Cambiar el estado para que entre en la "piscina" de asignación
        solicitud.estado = SolicitudCredito.ESTADO_EN_ASIGNACION
        solicitud.save()

        # Intentar asignar la solicitud inmediatamente
        asignar_solicitud_a_analista(solicitud.id)

        messages.info(request, f"Solicitud #{solicitud.id} enviada a la cola de asignación.")

    return redirect('solicitud_detalle', solicitud_id=solicitud_id)





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
            
            messages.success(request, f'Solicitud #{solicitud.id} creada. Resultado: {observacion_motor}')
            return redirect('listar_solicitudes') 

    else:
        form = SolicitudCreditoForm()
        
    return render(request, 'creditos/crear_solicitud.html', {'form': form})

@login_required
def listar_solicitudes_view(request):
    solicitudes_del_asesor = SolicitudCredito.objects.filter(asesor_comercial=request.user)
    contexto = {'solicitudes': solicitudes_del_asesor}
    return render(request, 'creditos/listar_solicitudes.html', contexto)

@login_required
def solicitud_detalle_view(request, solicitud_id):
    solicitud = get_object_or_404(SolicitudCredito, id=solicitud_id)
    
    if request.user != solicitud.asesor_comercial:
        messages.error(request, "No tienes permiso para ver esta solicitud.")
        return redirect('listar_solicitudes')

    form_documento = DocumentoForm()

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

    contexto = {
        'solicitud': solicitud,
        'form_documento': form_documento
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
    
    return redirect('solicitud_detalle', solicitud_id=solicitud_id)

# --- VISTAS DEL ANALISTA ---

@login_required
def analista_dashboard_view(request):
    # 1. Verificación inicial del perfil y la solicitud asignada
    if not hasattr(request.user, 'perfil'):
        messages.error(request, "No tienes un perfil de usuario asignado.")
        return redirect('/') # Redirigir a una página de inicio

    solicitud_asignada = request.user.perfil.solicitud_actual
    if not solicitud_asignada:
        return render(request, 'creditos/analista_dashboard.html', {'solicitud': None})

    # 2. Procesamiento de formularios si la petición es POST
    if request.method == 'POST':
        if 'submit_documento' in request.POST:
            form_documento = DocumentoAnalisisForm(request.POST, request.FILES)
            if form_documento.is_valid():
                doc = form_documento.save(commit=False)
                doc.solicitud = solicitud_asignada
                doc.subido_por = request.user
                doc.save()
                messages.success(request, f"Documento '{doc.get_nombre_documento_display()}' cargado exitosamente.")
            else:
                messages.error(request, "Error al cargar el documento.")
            return redirect('analista_dashboard')

        elif 'submit_observacion' in request.POST:
            form_observacion = ObservacionAnalisisForm(request.POST, instance=solicitud_asignada)
            if form_observacion.is_valid():
                form_observacion.save()
                messages.success(request, "Observación guardada.")
            return redirect('analista_dashboard')

        elif 'submit_riesgo' in request.POST:
            form_riesgo = AnalisisRiesgoForm(request.POST, instance=solicitud_asignada)
            if form_riesgo.is_valid():
                form_riesgo.save()
                
                # --- LÓGICA DE GUARDADO DE RECOMENDACIÓN ---
                aprobado, recomendacion_texto = ejecutar_motor_recomendacion(form_riesgo.cleaned_data)
                
                # Guardamos la recomendación en la base de datos
                solicitud_asignada.recomendacion_sistema_aprobada = aprobado
                solicitud_asignada.recomendacion_sistema_texto = recomendacion_texto
                solicitud_asignada.save()
                
                messages.info(request, "Recomendación del sistema generada y guardada.")
            # Redirigimos para mostrar el estado actualizado de la página
            return redirect('analista_dashboard')

    # 3. Preparación del contexto para renderizar la plantilla (peticiones GET y después de redirects)
    documentos_del_asesor = solicitud_asignada.documentos.filter(subido_por=solicitud_asignada.asesor_comercial)
    documentos_del_analista = solicitud_asignada.documentos.filter(subido_por=request.user)
    
    docs_obligatorios = {'HISTORIAL_CREDITO', 'PROCESOS_JUDICIALES'}
    docs_cargados_analista = {doc.nombre_documento for doc in documentos_del_analista}
    documentos_obligatorios_ok = docs_obligatorios.issubset(docs_cargados_analista)
    
    contexto = {
        'solicitud': solicitud_asignada,
        'form_documento': DocumentoAnalisisForm(),
        'form_observacion': ObservacionAnalisisForm(instance=solicitud_asignada),
        'form_riesgo': AnalisisRiesgoForm(instance=solicitud_asignada),
        'documentos_del_asesor': documentos_del_asesor,
        'documentos_del_analista': documentos_del_analista,
        'documentos_obligatorios_ok': documentos_obligatorios_ok,
    }
    
    return render(request, 'creditos/analista_dashboard.html', contexto)

@login_required
def preaprobar_solicitud_view(request, solicitud_id):
    solicitud = get_object_or_404(SolicitudCredito, id=solicitud_id, analista_asignado=request.user)
    
    # Cambiamos el estado, pero la acción principal es la redirección
    solicitud.estado = SolicitudCredito.ESTADO_PREAPROBADO
    solicitud.save()
    
    HistorialEstado.objects.create(
        solicitud=solicitud,
        estado_anterior=solicitud.estado, # El estado ya fue actualizado
        estado_nuevo=solicitud.ESTADO_PREAPROBADO,
        usuario_responsable=request.user,
        observaciones="Analista pre-aprobó la solicitud. Pasando a análisis de capacidad de pago."
    )
    
    messages.info(request, f"Solicitud #{solicitud_id} pre-aprobada. Por favor, complete el análisis de capacidad de pago.")
    # Redirigimos a la nueva vista
    return redirect('capacidad_pago', solicitud_id=solicitud.id)






@login_required
def rechazar_solicitud_view(request, solicitud_id):
    """
    Procesa la acción de rechazar una solicitud por parte de un analista.
    """
    # 1. Obtiene la solicitud, asegurando que el usuario logueado sea el analista asignado.
    #    Esto previene que un analista rechace solicitudes de otros.
    solicitud = get_object_or_404(SolicitudCredito, id=solicitud_id, analista_asignado=request.user)
    
    # 2. Guarda el estado anterior para el registro del historial
    estado_anterior = solicitud.estado
    
    # 3. Actualiza el estado de la solicitud a RECHAZADO_ANALISTA
    solicitud.estado = SolicitudCredito.ESTADO_RECHAZADO_ANALISTA
    solicitud.save()
    
    # 4. Crea un registro en el historial para auditar la acción
    HistorialEstado.objects.create(
        solicitud=solicitud,
        estado_anterior=estado_anterior,
        estado_nuevo=solicitud.estado,
        usuario_responsable=request.user,
        observaciones="Analista rechazó la solicitud después de la evaluación de riesgo."
    )

    # 5. Libera al analista para que pueda recibir una nueva solicitud
    #    Esto es crucial para el flujo de trabajo.
    request.user.perfil.solicitud_actual = None
    request.user.perfil.save()
    
    # 6. Muestra un mensaje de confirmación al analista
    messages.warning(request, f"Solicitud #{solicitud.id} ha sido RECHAZADA. Caso cerrado.")
    
    # 7. Dispara el mecanismo para buscar una nueva tarea en la cola
    #    Esta es la nueva lógica que añadimos.
    print(f"Analista {request.user.username} liberado. Buscando nueva solicitud en la cola...")
    intentar_asignar_solicitud_en_espera()

    # 8. Redirige al analista a su dashboard, donde verá una nueva solicitud o el mensaje de "Estás al día".
    return redirect('analista_dashboard')






@login_required
def capacidad_pago_view(request, solicitud_id):
    solicitud = get_object_or_404(SolicitudCredito, id=solicitud_id, analista_asignado=request.user)
    resultado_calculo = None

    if request.method == 'POST':
        form = CapacidadPagoForm(request.POST, instance=solicitud)
        if form.is_valid():
            # Guardamos los datos del formulario en el objeto solicitud
            instancia_guardada = form.save()
            messages.success(request, "Datos guardados correctamente.")
            
            # Llamamos al servicio con la instancia ya actualizada
            resultado_calculo = calcular_capacidad_pago_service(instancia_guardada)
            
            # Guardamos el resultado principal en la BD
            instancia_guardada.capacidad_pago_calculada = resultado_calculo.get('Capacidad de Pago Mensual', 0)
            instancia_guardada.save()

    else: # Petición GET
        form = CapacidadPagoForm(instance=solicitud)
        # Si ya se había calculado antes, lo mostramos al cargar la página
        if solicitud.capacidad_pago_calculada is not None:
             resultado_calculo = calcular_capacidad_pago_service(solicitud)

    contexto = {
        'solicitud': solicitud,
        'form': form,
        'resultado_calculo': resultado_calculo
    }
    return render(request, 'creditos/capacidad_pago.html', contexto)