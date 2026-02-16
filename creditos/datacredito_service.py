# creditos/datacredito_service.py
"""
Servicio de integración con DataCrédito.
Implementa dos APIs:
1. HPN REST API: Historia de Crédito + Advance Score (Z0) + Quanto (O4)
2. Reconocer Master API: Validación de identidad y ubicación
"""

import requests
import uuid
from datetime import datetime
from decimal import Decimal
from django.conf import settings
from django.utils import timezone

from .models import SolicitudCredito, ConsultaDataCredito


# ==============================================================================
# CÓDIGOS DE RESPUESTA DATACREDITO
# ==============================================================================

CODIGOS_RESPUESTA = {
    '09': 'Identificación no encontrada',
    '10': 'Apellido no coincide',
    '13': 'Consulta exitosa con datos',
    '14': 'Consulta exitosa sin datos en central',
    '99': 'Error técnico',
}

# Tipos de identificación DataCrédito
TIPO_ID_CEDULA = 1
TIPO_ID_NIT = 2
TIPO_ID_CEDULA_EXTRANJERIA = 3
TIPO_ID_PASAPORTE = 4


# ==============================================================================
# CLIENTE HPN (Historia de Crédito + Score + Quanto)
# ==============================================================================

class DataCreditoHPNClient:
    """
    Cliente para consumir el servicio HPN REST de DataCrédito.
    Obtiene Historia de Crédito, Advance Score y Quanto en una sola llamada.
    """

    def __init__(self):
        config = settings.DATACREDITO_HPN
        self.enabled = config['ENABLED']
        self.token_url = config['TOKEN_URL']
        self.api_url = config['API_URL']
        self.client_id = config['CLIENT_ID']
        self.client_secret = config['CLIENT_SECRET']
        self.username = config['USERNAME']
        self.password = config['PASSWORD']
        self.user = config['USER']
        self.user_password = config['USER_PASSWORD']
        self.product_id = config['PRODUCT_ID']
        self.server_ip = config['SERVER_IP']
        self._token = None
        self._token_expiry = None

    def _get_token(self) -> str:
        """
        Obtiene un token de acceso OAuth2.
        """
        if self._token and self._token_expiry and self._token_expiry > timezone.now():
            return self._token

        headers = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'Content-Type': 'application/json',
        }

        payload = {
            'username': self.username,
            'password': self.password,
        }

        try:
            response = requests.post(
                self.token_url,
                json=payload,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()

            data = response.json()
            self._token = data.get('access_token')
            expires_in = data.get('expires_in', 3600)
            self._token_expiry = timezone.now() + timezone.timedelta(seconds=expires_in - 60)

            return self._token

        except requests.RequestException as e:
            raise Exception(f"Error obteniendo token HPN: {str(e)}")

    def consultar(self, cedula: str, primer_apellido: str) -> dict:
        """
        Realiza la consulta al servicio HPN.

        Args:
            cedula: Número de cédula del solicitante
            primer_apellido: Primer apellido del solicitante

        Returns:
            dict con los datos de la consulta
        """
        if not self.enabled:
            return {
                'success': False,
                'error': 'Servicio HPN deshabilitado',
                'codigo': 'DISABLED'
            }

        try:
            token = self._get_token()

            headers = {
                'Content-Type': 'application/json',
                'serverIpAddress': self.server_ip,
                'ProductId': self.product_id,
                'InfoAccountType': '1',
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'Authorization': f'Bearer {token}',
            }

            payload = {
                'user': self.user,
                'password': self.user_password,
                'identifyingTrx': {
                    'requestUUID': str(uuid.uuid4()),
                    'dateTime': datetime.now().strftime('%Y-%m-%dT%H:%M:%S-05:00'),
                    'originatorChannelName': 'GCFS-WEBSERVICE',
                    'originatorChannelType': '42',
                },
                'identifyingUser': {
                    'person': {
                        'personId': {
                            'personIdNumber': cedula,
                            'personIdType': TIPO_ID_CEDULA,
                        },
                        'personLastName': primer_apellido.upper(),
                    }
                }
            }

            response = requests.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=60
            )

            if response.status_code == 401:
                self._token = None
                return {
                    'success': False,
                    'error': 'Token expirado o inválido',
                    'codigo': '401'
                }

            response.raise_for_status()
            data = response.json()

            return self._procesar_respuesta(data)

        except requests.Timeout:
            return {
                'success': False,
                'error': 'Timeout en consulta DataCrédito',
                'codigo': 'TIMEOUT'
            }
        except requests.RequestException as e:
            return {
                'success': False,
                'error': f'Error de conexión: {str(e)}',
                'codigo': 'CONNECTION_ERROR'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Error inesperado: {str(e)}',
                'codigo': 'UNKNOWN_ERROR'
            }

    def _procesar_respuesta(self, data: dict) -> dict:
        """
        Procesa la respuesta del servicio HPN y extrae los datos relevantes.
        """
        resultado = {
            'success': True,
            'respuesta_cruda': data,
            'codigo': None,
            'mensaje': None,
            'advance_score': None,
            'score_descripcion': None,
            'quanto_valor': None,
            'total_obligaciones': 0,
            'obligaciones_al_dia': 0,
            'obligaciones_mora': 0,
            'saldo_total': Decimal('0'),
            'saldo_mora': Decimal('0'),
            'cuota_mensual_total': Decimal('0'),
            'mora_telco': Decimal('0'),
            'mora_sector_real': Decimal('0'),
            'mora_sector_financiero': Decimal('0'),
            'huellas_ultimos_6_meses': 0,
            'vector_comportamiento': [],
        }

        # Código de respuesta
        response_info = data.get('responseInfo', {})
        resultado['codigo'] = response_info.get('responseCode', '')
        resultado['mensaje'] = response_info.get('responseMessage', '')

        # Validar código de respuesta
        if resultado['codigo'] == '09':
            resultado['success'] = False
            resultado['error'] = 'Identificación no encontrada en DataCrédito'
            return resultado
        elif resultado['codigo'] == '10':
            resultado['success'] = False
            resultado['error'] = 'El apellido no coincide con la identificación'
            return resultado
        elif resultado['codigo'] == '14':
            resultado['success'] = True
            resultado['sin_datos'] = True
            return resultado

        # Extraer Score (Advance Score Z0)
        models = data.get('models', [])
        for model in models:
            if model.get('modelId') == 'Z0':  # Advance Score
                resultado['advance_score'] = model.get('score')
                resultado['score_descripcion'] = model.get('scoreDescription', '')
            elif model.get('modelId') == 'O4':  # Quanto
                quanto_val = model.get('score') or model.get('value')
                if quanto_val:
                    try:
                        resultado['quanto_valor'] = Decimal(str(quanto_val))
                    except:
                        pass

        # Extraer resumen de cartera
        credit_info = data.get('creditInformation', {})
        summary = credit_info.get('summary', {})

        resultado['total_obligaciones'] = summary.get('totalAccounts', 0)
        resultado['obligaciones_al_dia'] = summary.get('currentAccounts', 0)
        resultado['obligaciones_mora'] = summary.get('delinquentAccounts', 0)

        # Saldos
        try:
            resultado['saldo_total'] = Decimal(str(summary.get('totalBalance', 0) or 0))
            resultado['saldo_mora'] = Decimal(str(summary.get('delinquentBalance', 0) or 0))
            resultado['cuota_mensual_total'] = Decimal(str(summary.get('totalPayment', 0) or 0))
        except:
            pass

        # Extraer moras por sector
        sectors = credit_info.get('sectors', [])
        for sector in sectors:
            sector_name = sector.get('sectorName', '').upper()
            mora = Decimal(str(sector.get('delinquentBalance', 0) or 0))

            if 'TELECOM' in sector_name or 'TELCO' in sector_name:
                resultado['mora_telco'] += mora
            elif 'REAL' in sector_name:
                resultado['mora_sector_real'] += mora
            elif 'FINANC' in sector_name:
                resultado['mora_sector_financiero'] += mora

        # Extraer huellas de consulta (últimos 6 meses)
        inquiries = data.get('inquiries', {})
        resultado['huellas_ultimos_6_meses'] = inquiries.get('last6Months', 0)

        # Extraer vector de comportamiento (24 meses)
        accounts = credit_info.get('accounts', [])
        if accounts:
            for account in accounts[:5]:  # Solo las primeras 5 cuentas
                payment_history = account.get('paymentHistory', [])
                if payment_history:
                    resultado['vector_comportamiento'].append({
                        'entidad': account.get('subscriberName', ''),
                        'tipo': account.get('accountType', ''),
                        'historial': payment_history[:24],  # Últimos 24 meses
                    })

        return resultado


# ==============================================================================
# CLIENTE RECONOCER MASTER
# ==============================================================================

class DataCreditoReconocerClient:
    """
    Cliente para consumir el servicio Reconocer Master de DataCrédito.
    Obtiene información de ubicación e identidad.
    """

    def __init__(self):
        config = settings.DATACREDITO_RECONOCER
        self.enabled = config['ENABLED']
        self.token_url = config['TOKEN_URL']
        self.api_url = config['API_URL']
        self.client_id = config['CLIENT_ID']
        self.client_secret = config['CLIENT_SECRET']
        self.authorization = config['AUTHORIZATION']
        self.username = config['USERNAME']
        self.password = config['PASSWORD']
        self.scope = config['SCOPE']
        self.nit = config['NIT']
        self._token = None
        self._token_expiry = None

    def _get_token(self) -> str:
        """
        Obtiene un token de acceso OAuth2 para Reconocer.
        Usa grant_type=password con Okta.
        """
        if self._token and self._token_expiry and self._token_expiry > timezone.now():
            return self._token

        headers = {
            'Authorization': self.authorization,
            'accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded',
        }

        data = {
            'grant_type': 'password',
            'username': self.username,
            'password': self.password,
            'scope': self.scope,
        }

        try:
            response = requests.post(
                self.token_url,
                data=data,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()

            token_data = response.json()
            self._token = token_data.get('access_token')
            expires_in = token_data.get('expires_in', 3600)
            self._token_expiry = timezone.now() + timezone.timedelta(seconds=expires_in - 60)

            return self._token

        except requests.RequestException as e:
            raise Exception(f"Error obteniendo token Reconocer: {str(e)}")

    def consultar(self, cedula: str, primer_apellido: str) -> dict:
        """
        Realiza la consulta al servicio Reconocer Master.

        Args:
            cedula: Número de cédula del solicitante
            primer_apellido: Primer apellido del solicitante

        Returns:
            dict con los datos de ubicación
        """
        if not self.enabled:
            return {
                'success': False,
                'error': 'Servicio Reconocer deshabilitado',
                'codigo': 'DISABLED'
            }

        try:
            token = self._get_token()

            headers = {
                'access_token': token,
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'accept': 'application/json',
                'Content-Type': 'application/x-www-form-urlencoded',
            }

            params = {
                'tipoId': '2',  # NIT de la empresa consultante
                'numeroId': self.nit,
                'nit': self.nit,
                'tipoIdBuscar': '1',  # Cédula
                'numeroIdBuscar': cedula,
                'primerApellidoBuscar': primer_apellido.lower(),
                'validarNombre': 'false',
            }

            response = requests.get(
                self.api_url,
                params=params,
                headers=headers,
                timeout=30
            )

            if response.status_code == 401:
                self._token = None
                return {
                    'success': False,
                    'error': 'Token expirado o inválido',
                    'codigo': '401'
                }

            response.raise_for_status()
            data = response.json()

            return self._procesar_respuesta(data)

        except requests.Timeout:
            return {
                'success': False,
                'error': 'Timeout en consulta Reconocer',
                'codigo': 'TIMEOUT'
            }
        except requests.RequestException as e:
            return {
                'success': False,
                'error': f'Error de conexión: {str(e)}',
                'codigo': 'CONNECTION_ERROR'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Error inesperado: {str(e)}',
                'codigo': 'UNKNOWN_ERROR'
            }

    def _procesar_respuesta(self, data: dict) -> dict:
        """
        Procesa la respuesta del servicio Reconocer Master.
        """
        resultado = {
            'success': True,
            'respuesta_cruda': data,
            'codigo': None,
            'mensaje': None,
            'ciudad': None,
            'departamento': None,
            'direccion': None,
            'estrato': None,
            'telefono': None,
            'celular': None,
            'email': None,
        }

        # Código de respuesta
        response_info = data.get('responseInfo', {})
        resultado['codigo'] = response_info.get('responseCode', '')
        resultado['mensaje'] = response_info.get('responseMessage', '')

        if resultado['codigo'] not in ['13', '14', '']:
            resultado['success'] = False
            resultado['error'] = CODIGOS_RESPUESTA.get(
                resultado['codigo'],
                f"Error desconocido: {resultado['codigo']}"
            )
            return resultado

        # Extraer datos de ubicación
        location_info = data.get('locationInfo', {})
        if location_info:
            address = location_info.get('address', {})
            resultado['ciudad'] = address.get('city', '')
            resultado['departamento'] = address.get('state', '')
            resultado['direccion'] = address.get('streetAddress', '')
            resultado['estrato'] = address.get('stratum', '')

            # Contactos
            contacts = location_info.get('contacts', {})
            phones = contacts.get('phones', [])
            if phones:
                for phone in phones:
                    phone_type = phone.get('type', '').upper()
                    number = phone.get('number', '')
                    if 'CEL' in phone_type or 'MOVIL' in phone_type:
                        resultado['celular'] = number
                    else:
                        resultado['telefono'] = number

            emails = contacts.get('emails', [])
            if emails:
                resultado['email'] = emails[0].get('address', '')

        return resultado


# ==============================================================================
# FUNCIONES PRINCIPALES DE INTEGRACIÓN
# ==============================================================================

def consultar_datacredito(solicitud: SolicitudCredito) -> dict:
    """
    Ejecuta las consultas a DataCrédito (HPN y Reconocer) para una solicitud.

    Args:
        solicitud: Instancia de SolicitudCredito

    Returns:
        dict con los resultados combinados de ambas consultas
    """
    cedula = solicitud.cedula
    nombre_completo = solicitud.nombre_completo
    primer_apellido = nombre_completo.split()[-1] if nombre_completo else ''

    resultado = {
        'success': True,
        'hpn': None,
        'reconocer': None,
        'rechazar': False,
        'motivo_rechazo': None,
    }

    # 1. Consulta HPN (Historia de Crédito + Score + Quanto)
    hpn_client = DataCreditoHPNClient()
    resultado_hpn = hpn_client.consultar(cedula, primer_apellido)

    # Guardar consulta HPN en BD
    if resultado_hpn.get('success'):
        estado = ConsultaDataCredito.ESTADO_EXITO
        if resultado_hpn.get('sin_datos'):
            estado = ConsultaDataCredito.ESTADO_SIN_DATOS
    elif resultado_hpn.get('codigo') == '09':
        estado = ConsultaDataCredito.ESTADO_NO_ENCONTRADO
    else:
        estado = ConsultaDataCredito.ESTADO_ERROR

    consulta_hpn = ConsultaDataCredito.objects.create(
        solicitud=solicitud,
        tipo_consulta='HPN',
        estado_consulta=estado,
        codigo_respuesta=resultado_hpn.get('codigo'),
        mensaje_respuesta=resultado_hpn.get('mensaje') or resultado_hpn.get('error'),
        advance_score=resultado_hpn.get('advance_score'),
        score_descripcion=resultado_hpn.get('score_descripcion'),
        quanto_valor=resultado_hpn.get('quanto_valor'),
        total_obligaciones=resultado_hpn.get('total_obligaciones'),
        obligaciones_al_dia=resultado_hpn.get('obligaciones_al_dia'),
        obligaciones_mora=resultado_hpn.get('obligaciones_mora'),
        saldo_total=resultado_hpn.get('saldo_total'),
        saldo_mora=resultado_hpn.get('saldo_mora'),
        cuota_mensual_total=resultado_hpn.get('cuota_mensual_total'),
        mora_telco=resultado_hpn.get('mora_telco'),
        mora_sector_real=resultado_hpn.get('mora_sector_real'),
        mora_sector_financiero=resultado_hpn.get('mora_sector_financiero'),
        huellas_ultimos_6_meses=resultado_hpn.get('huellas_ultimos_6_meses'),
        vector_comportamiento=resultado_hpn.get('vector_comportamiento'),
        respuesta_cruda=resultado_hpn.get('respuesta_cruda'),
    )

    resultado['hpn'] = resultado_hpn

    # 2. Consulta Reconocer Master
    reconocer_client = DataCreditoReconocerClient()
    resultado_reconocer = reconocer_client.consultar(cedula, primer_apellido)

    # Guardar consulta Reconocer en BD
    if resultado_reconocer.get('success'):
        estado_rec = ConsultaDataCredito.ESTADO_EXITO
    else:
        estado_rec = ConsultaDataCredito.ESTADO_ERROR

    consulta_reconocer = ConsultaDataCredito.objects.create(
        solicitud=solicitud,
        tipo_consulta='RECONOCER',
        estado_consulta=estado_rec,
        codigo_respuesta=resultado_reconocer.get('codigo'),
        mensaje_respuesta=resultado_reconocer.get('mensaje') or resultado_reconocer.get('error'),
        reconocer_ciudad=resultado_reconocer.get('ciudad'),
        reconocer_departamento=resultado_reconocer.get('departamento'),
        reconocer_direccion=resultado_reconocer.get('direccion'),
        reconocer_estrato=resultado_reconocer.get('estrato'),
        reconocer_telefono=resultado_reconocer.get('telefono'),
        reconocer_celular=resultado_reconocer.get('celular'),
        reconocer_email=resultado_reconocer.get('email'),
        respuesta_cruda=resultado_reconocer.get('respuesta_cruda'),
    )

    resultado['reconocer'] = resultado_reconocer

    # 3. Evaluar reglas de rechazo basadas en DataCrédito
    resultado = evaluar_reglas_datacredito(resultado)

    return resultado


def evaluar_reglas_datacredito(resultado: dict) -> dict:
    """
    Evalúa las reglas de negocio basadas en los resultados de DataCrédito.

    Reglas de rechazo automático:
    1. Advance Score < 300 (muy alto riesgo)
    2. Mora en Telco > $300,000
    3. Mora en Sector Real/Financiero > $500,000
    4. Más de 3 huellas de consulta en últimos 6 meses
    """
    hpn = resultado.get('hpn', {})

    if not hpn or not hpn.get('success'):
        return resultado

    motivos = []

    # Regla 1: Score muy bajo
    score = hpn.get('advance_score')
    if score and score < 300:
        motivos.append(f"Score de riesgo muy bajo ({score})")

    # Regla 2: Mora en Telco
    mora_telco = hpn.get('mora_telco', Decimal('0'))
    if mora_telco and mora_telco > Decimal('300000'):
        motivos.append(f"Mora en Telco superior a $300,000 (${mora_telco:,.0f})")

    # Regla 3: Mora en otros sectores
    mora_otros = (hpn.get('mora_sector_real', Decimal('0')) or Decimal('0')) + \
                 (hpn.get('mora_sector_financiero', Decimal('0')) or Decimal('0'))
    if mora_otros > Decimal('500000'):
        motivos.append(f"Mora en sector real/financiero superior a $500,000 (${mora_otros:,.0f})")

    # Regla 4: Muchas huellas de consulta
    huellas = hpn.get('huellas_ultimos_6_meses', 0)
    if huellas and huellas > 3:
        motivos.append(f"Exceso de consultas en centrales ({huellas} en últimos 6 meses)")

    if motivos:
        resultado['rechazar'] = True
        resultado['motivo_rechazo'] = "; ".join(motivos)

    return resultado


def actualizar_solicitud_con_datacredito(solicitud: SolicitudCredito, resultado_dc: dict):
    """
    Actualiza los campos de la solicitud con los datos obtenidos de DataCrédito.
    """
    hpn = resultado_dc.get('hpn', {})

    if hpn and hpn.get('success'):
        # Actualizar campos de análisis en la solicitud
        solicitud.mora_telco_mayor_300k = (hpn.get('mora_telco') or Decimal('0')) > Decimal('300000')
        mora_otros = (hpn.get('mora_sector_real') or Decimal('0')) + \
                     (hpn.get('mora_sector_financiero') or Decimal('0'))
        solicitud.mora_otros_mayor_500k = mora_otros > Decimal('500000')
        solicitud.huellas_consulta = hpn.get('huellas_ultimos_6_meses', 0)

        # Gastos financieros (cuota mensual de obligaciones)
        cuota_total = hpn.get('cuota_mensual_total')
        if cuota_total and cuota_total > 0:
            solicitud.gastos_financieros = cuota_total

        solicitud.save()

    reconocer = resultado_dc.get('reconocer', {})
    if reconocer and reconocer.get('success'):
        # Actualizar datos de ubicación si vienen de Reconocer
        if reconocer.get('ciudad'):
            solicitud.ciudad_residencia = reconocer.get('ciudad')
        if reconocer.get('departamento'):
            solicitud.departamento_residencia = reconocer.get('departamento')
        if reconocer.get('direccion'):
            solicitud.direccion_residencia = reconocer.get('direccion')
        if reconocer.get('estrato'):
            try:
                solicitud.estrato = int(reconocer.get('estrato'))
            except (ValueError, TypeError):
                pass

        solicitud.save()
