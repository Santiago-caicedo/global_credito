from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import SolicitudCreditoForm,  DocumentoForm, ObservacionesAnalistaForm, ReferenciaForm
from .services import ejecutar_motor_inicial
from .models import HistorialEstado, SolicitudCredito, Documento, Referencia
from .services import asignar_solicitud_a_analista

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
    form_documento = DocumentoForm()

    if request.method == 'POST':
        # Esta sección se ejecuta solo si se envía el formulario de carga
        form = DocumentoForm(request.POST, request.FILES)
        if form.is_valid():
            nuevo_documento = form.save(commit=False)
            nuevo_documento.solicitud = solicitud
            nuevo_documento.save()
            messages.success(request, f"Documento '{nuevo_documento.get_nombre_documento_display()}' cargado exitosamente.")
            return redirect('solicitud_detalle', solicitud_id=solicitud.id)
        else:
            messages.error(request, "Error al cargar el documento. Por favor, intente de nuevo.")

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
def analista_dashboard_view(request):
    if not hasattr(request.user, 'perfil'):
        messages.error(request, "No tienes un perfil de usuario asignado.")
        return redirect('listar_solicitudes') # Redirigir a un lugar seguro

    solicitud_asignada = request.user.perfil.solicitud_actual

    # Si no hay solicitud, mostramos el dashboard vacío
    if not solicitud_asignada:
        return render(request, 'creditos/analista_dashboard.html', {'solicitud': None})

    # Si la petición es POST, significa que se envió un formulario
    if request.method == 'POST':
        # Usamos el nombre del botón de submit para saber qué formulario se envió
        if 'submit_observaciones' in request.POST:
            form_observaciones = ObservacionesAnalistaForm(request.POST, instance=solicitud_asignada)
            if form_observaciones.is_valid():
                form_observaciones.save()
                messages.success(request, "Observaciones guardadas correctamente.")
            else:
                messages.error(request, "Error al guardar las observaciones.")
        
        elif 'submit_referencia' in request.POST:
            form_referencia = ReferenciaForm(request.POST)
            if form_referencia.is_valid():
                nueva_referencia = form_referencia.save(commit=False)
                nueva_referencia.solicitud = solicitud_asignada
                nueva_referencia.save()
                messages.success(request, "Referencia añadida correctamente.")
            else:
                messages.error(request, "Error al añadir la referencia.")
        
        # Redirigir a la misma página para evitar reenvío de formulario
        return redirect('analista_dashboard')

    # Si la petición es GET, inicializamos los formularios vacíos
    form_observaciones = ObservacionesAnalistaForm(instance=solicitud_asignada)
    form_referencia = ReferenciaForm()

    contexto = {
        'solicitud': solicitud_asignada,
        'form_observaciones': form_observaciones,
        'form_referencia': form_referencia,
    }
    return render(request, 'creditos/analista_dashboard.html', contexto)