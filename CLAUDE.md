# Global Care Financial Services - Sistema de Creditos

## Descripcion General

Sistema de gestion de solicitudes de credito para **Global Care Financial Services** ("Alianzas de Bienestar"). Permite a aspirantes aplicar a creditos de forma publica, y gestiona el flujo interno de analisis y aprobacion con integracion a centrales de riesgo (DataCredito/Experian).

## Stack Tecnologico

- **Backend:** Django 5.2.3
- **Base de datos:** PostgreSQL
- **Frontend:** Bootstrap 5.3.3, Bootstrap Icons
- **Tipografia:** Cormorant Garamond (titulos), Montserrat (cuerpo)
- **Autenticacion:** Django Auth (django-axes desactivado temporalmente)
- **Email:** SMTP configurable (desarrollo usa consola)
- **Debug:** Django Debug Toolbar (solo desarrollo)
- **APIs Externas:** DataCredito/Experian (HPN + Reconocer Master)

## Identidad de Marca

### Colores
```css
--gc-azul-oscuro: #4d5572;
--gc-azul-medio: #7a87a5;
--gc-verde-salvia: #a3b38d;
--gc-gris-claro: #e2dfdd;
--gc-arena: #f0efef;
--gc-dorado: #c9a86c;
```

### Logo
- Ubicacion: `/static/img/logo-globalcare.png`
- En emails: Se pasa como `logo_url` en el contexto
- Dimensiones recomendadas: 180px en emails, 360px en web

## Estructura del Proyecto

```
global_credito/
├── core_credito/                    # Configuracion principal Django
│   ├── settings.py                  # Config DB, email, sesiones, DataCredito
│   ├── urls.py                      # URLs raiz
│   └── wsgi.py
├── creditos/                        # App principal de creditos
│   ├── models.py                    # SolicitudCredito, Documento, ConsultaDataCredito, etc.
│   ├── views.py                     # Vistas de analista y director
│   ├── views_publico.py             # Vistas publicas y de aspirante
│   ├── forms.py                     # Formularios
│   ├── services.py                  # Logica de negocio (motores, calculos, emails)
│   ├── datacredito_service.py       # Integracion con APIs de DataCredito
│   ├── decorators.py                # @aspirante_required, @analista_required, etc.
│   ├── urls.py                      # URLs internas (analista, director)
│   ├── urls_publico.py              # URLs publicas (/aplicar/, /mi-solicitud/)
│   ├── management/
│   │   └── commands/
│   │       └── test_datacredito.py  # Comando para probar APIs
│   └── templates/
│       ├── creditos/
│       │   ├── publico/             # aplicar.html, rechazado.html, registro.html
│       │   ├── aspirante/           # escritorio.html
│       │   ├── analista/            # Escritorio, caso activo, historial
│       │   └── director/            # Escritorio, detalle, pendientes
│       └── emails/                  # Templates de email HTML
├── usuarios/                        # App de usuarios
│   ├── models.py                    # PerfilUsuario con roles
│   ├── admin.py                     # Admin personalizado con roles inline
│   ├── signals.py                   # Señales para auto-asignacion
│   └── templates/usuarios/
├── templates/                       # Templates globales
│   ├── base.html
│   ├── base_publico.html
│   └── partials/
├── static/                          # Archivos estaticos (desarrollo)
├── staticfiles/                     # Archivos estaticos (produccion)
├── info/                            # Credenciales y colecciones Postman DataCredito
│   ├── WS_GCFS_HPN_Z0_O4_DEMO.txt
│   ├── WS_GCFS_RECONOCER MASTER_DEMO.txt
│   ├── _HPN_REST.postman_collection.json
│   └── RECONOCER_MASTER_DEMO.postman_collection.json
├── Manuales_WS_REST_HPN/            # Documentacion DataCredito
│   ├── 1. Instructivos/
│   │   ├── Instructivo cargue bases demo.pdf
│   │   └── MACRO CARGAR ID DEMO.xlsx
│   ├── 2. Formatos/
│   └── 4. Manuales Web Service/
├── test_api_datacredito.py          # Script standalone para probar APIs
└── .env                             # Variables de entorno (no commitear)
```

## Roles de Usuario

| Rol | Descripcion | Acceso |
|-----|-------------|--------|
| **ASPIRANTE** | Persona que solicita credito | `/mi-solicitud/` |
| **ANALISTA** | Evalua solicitudes asignadas | `/analista/` |
| **DIRECTOR** | Aprueba/rechaza, gestiona parametros | `/director/` |

## Flujo de Solicitud (con DataCredito)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  PASO 1: FORMULARIO PUBLICO (/aplicar/)                                     │
│  - Aspirante llena: cedula, nombre, fecha_nacimiento, ocupacion, ingresos   │
│  - Confirma datos en pantalla de revision                                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  PASO 2: MOTOR INICIAL (local, sin API externa)                             │
│  Valida:                                                                    │
│    ✓ Edad entre 18-65 años                                                  │
│    ✓ Ingresos >= $2,000,000 (empleado) o >= $3,000,000 (independiente)      │
│                                                                             │
│  SI RECHAZADO → Email rechazo genérico → FIN                                │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │ (si pasa)
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  PASO 3: CONSULTA DATACREDITO (2 APIs en paralelo)                          │
│                                                                             │
│  3a. API HPN (Historia de Crédito + Advance Score Z0 + Quanto O4)           │
│      → Score de riesgo, obligaciones, moras, huellas de consulta            │
│                                                                             │
│  3b. API Reconocer Master                                                   │
│      → Ciudad, departamento, direccion, estrato, contacto                   │
│                                                                             │
│  → Se guardan resultados en tabla ConsultaDataCredito                       │
│  → Se actualizan campos de la solicitud con datos obtenidos                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  PASO 4: MOTOR DATACREDITO (evalúa reglas de riesgo)                        │
│                                                                             │
│  Reglas de rechazo automático:                                              │
│    ✗ Advance Score < 300 (muy alto riesgo)                                  │
│    ✗ Mora Telco > $300,000                                                  │
│    ✗ Mora Sector Real/Financiero > $500,000                                 │
│    ✗ Más de 3 huellas de consulta en últimos 6 meses                        │
│                                                                             │
│  SI RECHAZADO → Email rechazo genérico → FIN                                │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │ (si pasa)
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  PASO 5: PRE-APROBACIÓN                                                     │
│  - Se genera token de registro (expira en 24h)                              │
│  - Email con link: /aplicar/registro/{token}/                               │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  PASO 6: REGISTRO Y DOCUMENTOS                                              │
│  - Aspirante crea cuenta desde el link del email                            │
│  - Sube documentos iniciales (cedula, renta, laboral, autorizacion)         │
│  - Envia a asignacion de analista                                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  PASOS 7-10: ANALISIS Y APROBACION                                          │
│  - Asignacion automatica a analista                                         │
│  - Analisis de documentos y capacidad de pago                               │
│  - Documentos finales (pagare, poliza, etc.)                                │
│  - Aprobacion/rechazo por Director                                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Estados de Solicitud

| Constante | Display | Descripcion |
|-----------|---------|-------------|
| `NUEVO` | Nuevo | Recien creada |
| `RECHAZADO_AUTO` | Rechazado Automaticamente | No paso motor inicial o DataCredito |
| `PEND_DOCUMENTOS` | Pendiente Carga Documentos | Esperando docs iniciales |
| `DOCS_CORRECCION` | Documentos en Correccion | Aspirante debe corregir |
| `EN_ASIGNACION` | En Espera de Asignacion | Cola para analista |
| `EN_ANALISIS` | En Analisis por Analista | Analista revisando |
| `PREAPROBADO` | Pre-Aprobado por Analista | Paso revision inicial |
| `PEND_DOCS_ADICIONALES` | Pendiente Documentos Adicionales | Esperando docs finales |
| `DOCS_FINALES_CORRECCION` | Correccion Docs Finales | Corrigiendo docs finales |
| `EN_VALIDACION_DOCS` | En Validacion de Documentos | Analista valida docs finales |
| `PEND_APROB_DIRECTOR` | Pendiente Aprobacion Director | Director debe decidir |
| `APROBADO` | Aprobado Final | Credito aprobado |
| `RECHAZADO_ANALISTA` | Rechazado por Analista | - |
| `RECHAZADO_DIRECTOR` | Rechazado por Director | - |

## Modelos Principales

### SolicitudCredito (`creditos/models.py`)
- Campos del formulario inicial (cedula, nombre, fecha_nacimiento, ocupacion, ingresos, monto_solicitado, plazo)
- Campos de contacto (email_aspirante, telefono_aspirante)
- Campos de analisis (tipo_vivienda, gastos, direccion, etc.)
- Campos de motor (mora_telco, mora_otros, huellas_consulta, etc.)
- Campos de oferta (capacidad_pago_calculada, monto_aprobado_calculado, plazo_oferta)
- Campos de token (token_registro, token_expiracion)
- Relaciones (aspirante, analista_asignado)

### ConsultaDataCredito (`creditos/models.py`)
Almacena cada consulta realizada a DataCredito para auditoria:
```python
ConsultaDataCredito:
  - solicitud (FK)
  - tipo_consulta ('HPN' | 'RECONOCER')
  - estado_consulta ('EXITO' | 'ERROR' | 'SIN_DATOS' | 'NO_ENCONTRADO')
  - fecha_consulta
  - codigo_respuesta, mensaje_respuesta

  # Datos HPN
  - advance_score (int, rango 150-950)
  - score_descripcion
  - quanto_valor (Decimal)
  - total_obligaciones, obligaciones_al_dia, obligaciones_mora
  - saldo_total, saldo_mora, cuota_mensual_total
  - mora_telco, mora_sector_real, mora_sector_financiero
  - huellas_ultimos_6_meses
  - vector_comportamiento (JSON, historico 24 meses)

  # Datos Reconocer
  - reconocer_ciudad, reconocer_departamento, reconocer_direccion
  - reconocer_estrato, reconocer_telefono, reconocer_celular, reconocer_email

  - respuesta_cruda (JSON completo para debug)
```

### Documento
- Tipos iniciales: CEDULA, DECLARACION_RENTA, CERTIFICADO_LABORAL, AUTORIZACION_CONSULTA
- Tipos finales: PAGARE, CARTA_INSTRUCCIONES, POLIZA_SEGURO, FORMATO_VINCULACION
- Campos: archivo, ok_analista, observacion_correccion, subido_por

### HistorialEstado
- Registro de cada cambio de estado
- Campos: estado_anterior, estado_nuevo, observaciones, usuario_responsable, fecha

### NotificacionEmail
- Auditoria de emails enviados
- Campos: tipo, email_destino, asunto, enviado, fecha_envio, error_mensaje

### ParametrosGlobales
- Singleton (pk=1) configurado por Director
- Campos: tasa_interes_mensual, porcentaje_seguro, porcentaje_fgs

## Integracion DataCredito

### APIs Implementadas

| API | Productos | Endpoint |
|-----|-----------|----------|
| **HPN REST** | Historia de Credito + Advance Score Z0 + Quanto O4 | `POST /cs/credit-history/v1/hdcplus` |
| **Reconocer Master** | Ubicacion + Contacto + Identidad | `GET /cs/reconocer/v1/location-info` |

### Archivos de la Integracion

| Archivo | Descripcion |
|---------|-------------|
| `creditos/datacredito_service.py` | Clientes API HPN y Reconocer |
| `creditos/models.py` | Modelo `ConsultaDataCredito` |
| `creditos/views_publico.py` | Integracion en flujo de aplicacion |
| `core_credito/settings.py` | Configuracion `DATACREDITO_HPN` y `DATACREDITO_RECONOCER` |
| `creditos/management/commands/test_datacredito.py` | Comando Django para pruebas |
| `test_api_datacredito.py` | Script standalone para pruebas |

### Reglas de Rechazo Automatico

| Regla | Condicion | Descripcion |
|-------|-----------|-------------|
| Score bajo | Advance Score < 300 | Muy alto riesgo crediticio |
| Mora Telco | Mora > $300,000 | Mora en telecomunicaciones |
| Mora Otros | Mora > $500,000 | Mora en sector real/financiero |
| Huellas | > 3 en 6 meses | Exceso de consultas a centrales |

### Respuesta API HPN (datos extraidos)

```python
{
    'success': True,
    'codigo': '13',  # 13=con datos, 14=sin datos, 09=no encontrado
    'advance_score': 650,           # Puntaje 150-950
    'score_descripcion': 'Riesgo medio',
    'quanto_valor': 45000000.00,    # Patrimonio estimado
    'total_obligaciones': 5,
    'obligaciones_al_dia': 4,
    'obligaciones_mora': 1,
    'saldo_total': 12500000.00,
    'saldo_mora': 350000.00,
    'cuota_mensual_total': 850000.00,
    'mora_telco': 0.00,
    'mora_sector_real': 150000.00,
    'mora_sector_financiero': 200000.00,
    'huellas_ultimos_6_meses': 2,
    'vector_comportamiento': [...]  # Historico 24 meses por cuenta
}
```

### Respuesta API Reconocer (datos extraidos)

```python
{
    'success': True,
    'codigo': '13',
    'ciudad': 'BOGOTA D.C.',
    'departamento': 'CUNDINAMARCA',
    'direccion': 'CRA 15 # 85-42 APTO 302',
    'estrato': '4',
    'telefono': '6012345678',
    'celular': '3101234567',
    'email': 'juan.perez@email.com'
}
```

### Codigos de Respuesta DataCredito

| Codigo | Significado |
|--------|-------------|
| `09` | Identificacion no encontrada |
| `10` | Apellido no coincide con identificacion |
| `13` | Consulta exitosa con datos |
| `14` | Consulta exitosa sin datos en central |
| `99` | Error tecnico |

### Uso del Servicio

```python
from creditos.datacredito_service import consultar_datacredito, actualizar_solicitud_con_datacredito

# Ejecutar consulta completa (HPN + Reconocer)
resultado = consultar_datacredito(solicitud)

# resultado = {
#     'success': True,
#     'hpn': {...},           # Datos de Historia + Score + Quanto
#     'reconocer': {...},     # Datos de ubicacion
#     'rechazar': False,      # True si debe rechazarse por reglas
#     'motivo_rechazo': None  # Texto con motivos si rechazar=True
# }

# Actualizar campos de solicitud con datos obtenidos
actualizar_solicitud_con_datacredito(solicitud, resultado)
```

### Probar las APIs

**Opcion 1: Comando Django**
```bash
# Con datos de ejemplo
python manage.py test_datacredito

# Con cedula especifica
python manage.py test_datacredito --cedula 1119623677 --apellido bogota

# Solo HPN o solo Reconocer
python manage.py test_datacredito --solo-hpn
python manage.py test_datacredito --solo-reconocer
```

**Opcion 2: Script standalone (sin Django)**
```bash
python test_api_datacredito.py
python test_api_datacredito.py --cedula 1119623677 --apellido bogota
```

### Estado Actual de la Integracion

| Componente | Estado |
|------------|--------|
| Codigo de integracion | ✅ Completo |
| Modelo ConsultaDataCredito | ✅ Completo |
| Integracion en flujo | ✅ Completo |
| Autenticacion Reconocer | ✅ Funciona (probado) |
| Autenticacion HPN | ⏳ Requiere IP autorizada |
| Datos de prueba | ⏳ Requiere cargar cedulas en demo |

### Requisitos para Pruebas en Ambiente Demo

1. **Para API HPN:** Solicitar a DataCredito que autoricen la IP del servidor
2. **Para ambas APIs:** Cargar cedulas de prueba usando el Excel `MACRO CARGAR ID DEMO.xlsx`
   - Enviar archivo a: `connectivity_support@experian.com`
   - Formato: `NIT901290934_BASE_PRUEBAS_YYYYMMDD.txt`
   - Maximo 200 registros

### Deshabilitar Consultas (Desarrollo)

```env
DATACREDITO_HPN_ENABLED=False
DATACREDITO_RECONOCER_ENABLED=False
```

## Servicios (`creditos/services.py`)

| Funcion | Descripcion |
|---------|-------------|
| `ejecutar_motor_inicial(solicitud)` | Valida edad (18-65) e ingresos minimos |
| `ejecutar_motor_recomendacion(datos)` | Evalua centrales de riesgo |
| `asignar_solicitud_a_analista(id, notificar_espera)` | Asigna a analista libre |
| `intentar_asignar_solicitud_en_espera()` | Busca solicitud en cola |
| `calcular_capacidad_pago_service(solicitud)` | Calcula capacidad con tabla |
| `calcular_oferta_service(solicitud)` | Calcula monto maximo |
| `enviar_notificacion_email(solicitud, tipo, extra_context)` | Envia y registra email |

## Servicios DataCredito (`creditos/datacredito_service.py`)

| Funcion/Clase | Descripcion |
|---------------|-------------|
| `DataCreditoHPNClient` | Cliente para API HPN (Historia + Score + Quanto) |
| `DataCreditoReconocerClient` | Cliente para API Reconocer Master |
| `consultar_datacredito(solicitud)` | Ejecuta ambas consultas y evalua reglas |
| `evaluar_reglas_datacredito(resultado)` | Aplica reglas de rechazo automatico |
| `actualizar_solicitud_con_datacredito(solicitud, resultado)` | Actualiza campos de solicitud |

## Sistema de Notificaciones por Email

### Tipos de Notificacion

| Tipo | Cuando se envia | Template |
|------|-----------------|----------|
| `PREAPROBACION` | Pasa motor inicial + DataCredito | `preaprobacion.html` |
| `BIENVENIDA` | Usuario crea su cuenta | `bienvenida.html` |
| `EN_ESPERA` | No hay analistas libres | `en_espera.html` |
| `ASIGNADO` | Se asigna a un analista | `asignado.html` |
| `RECHAZO_MOTOR` | Rechazado por motor o DataCredito | `rechazo_motor.html` |
| `CAMBIO_ESTADO` | Solicitud avanza de estado | `cambio_estado.html` |
| `DOCUMENTOS_RECHAZADOS` | Docs necesitan correccion | `documentos_rechazados.html` |
| `APROBACION_FINAL` | Director aprueba | `aprobacion_final.html` |
| `RECHAZO` | Director rechaza | `rechazo.html` |

## URLs Principales

### Publicas (sin auth)

| URL | Vista | Descripcion |
|-----|-------|-------------|
| `/aplicar/` | `aplicar_credito_view` | Formulario publico |
| `/aplicar/rechazado/<id>/` | `aplicar_rechazado_view` | Pagina de rechazo |
| `/aplicar/registro/<token>/` | `aspirante_registro_view` | Crear cuenta |

### Aspirante (auth)

| URL | Vista | Descripcion |
|-----|-------|-------------|
| `/mi-solicitud/` | `aspirante_escritorio_view` | Dashboard |
| `/mi-solicitud/subir/` | `aspirante_subir_documento_view` | Subir doc |
| `/mi-solicitud/enviar/` | `aspirante_enviar_documentos_view` | Enviar a analista |

### Internas (auth)

| URL | Vista | Rol |
|-----|-------|-----|
| `/analista/` | `analista_escritorio_view` | ANALISTA |
| `/analista/caso/` | `analista_caso_activo_view` | ANALISTA |
| `/director/` | `director_escritorio_view` | DIRECTOR |
| `/director/pendientes/` | `director_pendientes_view` | DIRECTOR |

## Comandos Utiles

```bash
# Servidor de desarrollo
python manage.py runserver

# Migraciones (IMPORTANTE: ejecutar despues de actualizar codigo)
python manage.py makemigrations creditos
python manage.py migrate

# Crear usuarios de prueba
python manage.py crear_usuarios_prueba

# Probar configuracion de email
python manage.py test_email tu@email.com

# Probar conexion DataCredito
python manage.py test_datacredito
python manage.py test_datacredito --cedula 12345678 --apellido PEREZ

# Recolectar estaticos (produccion)
python manage.py collectstatic
```

## Variables de Entorno (.env)

```env
# Django
SECRET_KEY=tu-clave-secreta
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Base de datos
DB_NAME=global_db
DB_USER=postgres
DB_PASSWORD=password
DB_HOST=localhost
DB_PORT=5432

# Email
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=mail.tudominio.com
EMAIL_PORT=465
EMAIL_USE_SSL=True
EMAIL_USE_TLS=False
EMAIL_HOST_USER=info@tudominio.com
EMAIL_HOST_PASSWORD=tu-password
DEFAULT_FROM_EMAIL=Global Care F.S. <info@tudominio.com>

# URL base del sitio
SITE_URL=https://tudominio.com

# ============================================
# DataCredito - HPN REST API
# ============================================
DATACREDITO_HPN_ENABLED=True
DATACREDITO_HPN_TOKEN_URL=https://uat-api.datacredito.com.co/spla/oauth2/v1/token
DATACREDITO_HPN_API_URL=https://uat-api.datacredito.com.co/cs/credit-history/v1/hdcplus
DATACREDITO_HPN_CLIENT_ID=0oap0lmbt8DIofFZ10h7
DATACREDITO_HPN_CLIENT_SECRET=MyXK_QM0d_2ogXj84NIeOOYh8fBOK8ACkawRCvxj
DATACREDITO_HPN_USERNAME=2-901290934@demo.datacredito.com.co
DATACREDITO_HPN_PASSWORD=tIdH83j2W07h
DATACREDITO_HPN_USER=901290934
DATACREDITO_HPN_USER_PASSWORD=66WKB
DATACREDITO_HPN_PRODUCT_ID=64
DATACREDITO_HPN_SERVER_IP=181.234.87.83

# ============================================
# DataCredito - Reconocer Master API
# ============================================
DATACREDITO_RECONOCER_ENABLED=True
DATACREDITO_RECONOCER_TOKEN_URL=https://experian-latamb.oktapreview.com/oauth2/ausdbwi7pes71n0hU0h7/v1/token
DATACREDITO_RECONOCER_API_URL=https://demo-servicesesb.datacredito.com.co:444/cs/reconocer/v1/location-info
DATACREDITO_RECONOCER_CLIENT_ID=0oa2bv3uy1zgbsA600h8
DATACREDITO_RECONOCER_CLIENT_SECRET=ZkuOBIDrhALdA46Fu1zNaYLLhIQ4dECBd70o3Mt2wkFmvhBcilfzOI4hHWzKqg3L
DATACREDITO_RECONOCER_AUTHORIZATION=Basic MG9hMmJ2M3V5MXpnYnNBNjAwaDg6Wmt1T0JJRHJoQUxkQTQ2RnUxek5hWUxMaElRNGRFQ0JkNzBvM010MndrRm12aEJjaWxmek9JNGhIV3pLcWczTA==
DATACREDITO_RECONOCER_USERNAME=2-901290934.1@demo.datacredito.com.co
DATACREDITO_RECONOCER_PASSWORD=3y549oOkqHYS
DATACREDITO_RECONOCER_SCOPE=expco_reconocer_master
DATACREDITO_RECONOCER_NIT=901290934
```

## Logica de Asignacion de Analistas

```
Aspirante envía documentos → EN_ASIGNACION
                │
                ▼
    ¿Hay analista libre?
        │           │
       SÍ          NO
        │           │
        ▼           ▼
    Asignar     Queda en cola
    al azar     Email: EN_ESPERA
    Email:          │
    ASIGNADO        │ (espera)
        │           ▼
        └──> Cuando analista termina caso
             → intentar_asignar_en_espera()
```

## Logica de Reaplicacion

Cuando un usuario rechazado vuelve a aplicar con la misma cedula:

1. Sistema detecta solicitud existente en estado inactivo
2. **Actualiza** la solicitud existente en lugar de crear nueva
3. Resetea campos de analisis previo
4. Registra "Reaplicacion" en historial
5. Ejecuta motor inicial + DataCredito nuevamente

## Admin de Django

El admin ha sido personalizado para gestionar usuarios con roles:

- **Inline de Perfil:** Al editar un User, aparece seccion para asignar rol
- **Columna Rol:** Lista de usuarios muestra columna "Rol"
- **Filtro por Rol:** Filtro lateral permite filtrar usuarios por rol
- **Auto-asignacion:** Al guardar un analista libre, se asignan solicitudes en espera

## Notas de Desarrollo

- **django-axes:** Desactivado temporalmente
- **Sesiones:** Expiran en 15 minutos de inactividad (`SESSION_COOKIE_AGE=900`)
- **Debug Toolbar:** Solo visible con `DEBUG=True` desde `127.0.0.1`
- **Emails de rechazo:** No revelan motivo especifico (politica de UX)
- **DataCredito:** API HPN requiere IP autorizada, Reconocer funciona desde cualquier IP

## Dependencias

```bash
pip install django==5.2.3
pip install psycopg2-binary
pip install python-decouple
pip install requests  # Para DataCredito
pip install gunicorn  # Produccion
```

## Migracion Requerida

Despues de clonar o actualizar el codigo:

```bash
python manage.py makemigrations creditos
python manage.py migrate
```
