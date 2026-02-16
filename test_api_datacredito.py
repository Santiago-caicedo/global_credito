#!/usr/bin/env python3
"""
Script de prueba para las APIs de DataCrédito.
No requiere Django, solo Python 3 estándar.

Uso:
    python test_api_datacredito.py
    python test_api_datacredito.py --cedula 1119623677 --apellido bogota
"""

import urllib.request
import urllib.parse
import urllib.error
import json
import ssl
import sys
from datetime import datetime
import uuid

# Ignorar verificación SSL para pruebas (no usar en producción)
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# ==============================================================================
# CREDENCIALES HPN (del archivo .env)
# ==============================================================================
HPN_CONFIG = {
    'TOKEN_URL': 'https://uat-api.datacredito.com.co/spla/oauth2/v1/token',
    'API_URL': 'https://uat-api.datacredito.com.co/cs/credit-history/v1/hdcplus',
    'CLIENT_ID': '0oap0lmbt8DIofFZ10h7',
    'CLIENT_SECRET': 'MyXK_QM0d_2ogXj84NIeOOYh8fBOK8ACkawRCvxj',
    'USERNAME': '2-901290934@demo.datacredito.com.co',
    'PASSWORD': 'tIdH83j2W07h',
    'USER': '901290934',
    'USER_PASSWORD': '66WKB',
    'PRODUCT_ID': '65',
    'SERVER_IP': '34.237.16.176',
}

# ==============================================================================
# CREDENCIALES RECONOCER (del archivo .env)
# ==============================================================================
RECONOCER_CONFIG = {
    'TOKEN_URL': 'https://experian-latamb.oktapreview.com/oauth2/ausdbwi7pes71n0hU0h7/v1/token',
    'API_URL': 'https://demo-servicesesb.datacredito.com.co:444/cs/reconocer/v1/location-info',
    'CLIENT_ID': '0oa2bv3uy1zgbsA600h8',
    'CLIENT_SECRET': 'ZkuOBIDrhALdA46Fu1zNaYLLhIQ4dECBd70o3Mt2wkFmvhBcilfzOI4hHWzKqg3L',
    'AUTHORIZATION': 'Basic MG9hMmJ2M3V5MXpnYnNBNjAwaDg6Wmt1T0JJRHJoQUxkQTQ2RnUxek5hWUxMaElRNGRFQ0JkNzBvM010MndrRm12aEJjaWxmek9JNGhIV3pLcWczTA==',
    'USERNAME': '2-901290934.1@demo.datacredito.com.co',
    'PASSWORD': '3y549oOkqHYS',
    'SCOPE': 'expco_reconocer_master',
    'NIT': '901290934',
}


def http_request(url, method='GET', headers=None, data=None, json_data=None):
    """Realiza una petición HTTP."""
    headers = headers or {}

    if json_data:
        data = json.dumps(json_data).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    elif data and isinstance(data, dict):
        data = urllib.parse.urlencode(data).encode('utf-8')
        if 'Content-Type' not in headers:
            headers['Content-Type'] = 'application/x-www-form-urlencoded'

    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, context=ssl_context, timeout=60) as response:
            return {
                'status': response.status,
                'data': json.loads(response.read().decode('utf-8'))
            }
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8') if e.fp else ''
        try:
            body = json.loads(body)
        except:
            pass
        return {
            'status': e.code,
            'error': str(e),
            'data': body
        }
    except Exception as e:
        return {
            'status': 0,
            'error': str(e),
            'data': None
        }


def test_hpn(cedula, apellido):
    """Prueba la API HPN (Historia de Crédito + Score + Quanto)."""
    print("\n" + "="*60)
    print("API HPN (Historia de Crédito + Advance Score + Quanto)")
    print("="*60)

    # 1. Obtener Token
    print("\n[1] Obteniendo token de acceso...")

    token_headers = {
        'client_id': HPN_CONFIG['CLIENT_ID'],
        'client_secret': HPN_CONFIG['CLIENT_SECRET'],
        'Content-Type': 'application/json',
    }

    token_payload = {
        'username': HPN_CONFIG['USERNAME'],
        'password': HPN_CONFIG['PASSWORD'],
    }

    token_response = http_request(
        HPN_CONFIG['TOKEN_URL'],
        method='POST',
        headers=token_headers,
        json_data=token_payload
    )

    if token_response.get('status') != 200:
        print(f"    ERROR obteniendo token: {token_response}")
        return

    token = token_response['data'].get('access_token')
    print(f"    Token obtenido: {token[:50]}...")

    # 2. Consultar servicio
    print(f"\n[2] Consultando historia de crédito para cédula {cedula}...")

    api_headers = {
        'Content-Type': 'application/json',
        'serverIpAddress': HPN_CONFIG['SERVER_IP'],
        'ProductId': HPN_CONFIG['PRODUCT_ID'],
        'InfoAccountType': '1',
        'client_id': HPN_CONFIG['CLIENT_ID'],
        'client_secret': HPN_CONFIG['CLIENT_SECRET'],
        'Authorization': f'Bearer {token}',
    }

    api_payload = {
        'user': HPN_CONFIG['USER'],
        'password': HPN_CONFIG['USER_PASSWORD'],
        'identifyingTrx': {
            'requestUUID': str(uuid.uuid4()),
            'dateTime': datetime.now().strftime('%Y-%m-%dT%H:%M:%S-05:00'),
            'originatorChannelName': 'GCFS-TEST',
            'originatorChannelType': '42',
        },
        'identifyingUser': {
            'person': {
                'personId': {
                    'personIdNumber': cedula,
                    'personIdType': 1,
                },
                'personLastName': apellido.upper(),
            }
        }
    }

    api_response = http_request(
        HPN_CONFIG['API_URL'],
        method='POST',
        headers=api_headers,
        json_data=api_payload
    )

    print(f"\n[3] RESPUESTA (status: {api_response.get('status')}):")
    print("-"*60)

    if api_response.get('error'):
        print(f"ERROR: {api_response.get('error')}")

    data = api_response.get('data')
    if data:
        # Mostrar respuesta formateada
        print(json.dumps(data, indent=2, ensure_ascii=False)[:3000])
        if len(json.dumps(data)) > 3000:
            print("\n... (respuesta truncada)")

    return api_response


def test_reconocer(cedula, apellido):
    """Prueba la API Reconocer Master."""
    print("\n" + "="*60)
    print("API RECONOCER MASTER (Ubicación + Contacto)")
    print("="*60)

    # 1. Obtener Token (OAuth2 password grant con Okta)
    print("\n[1] Obteniendo token de acceso Okta...")

    token_headers = {
        'Authorization': RECONOCER_CONFIG['AUTHORIZATION'],
        'accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded',
    }

    token_data = {
        'grant_type': 'password',
        'username': RECONOCER_CONFIG['USERNAME'],
        'password': RECONOCER_CONFIG['PASSWORD'],
        'scope': RECONOCER_CONFIG['SCOPE'],
    }

    token_response = http_request(
        RECONOCER_CONFIG['TOKEN_URL'],
        method='POST',
        headers=token_headers,
        data=token_data
    )

    if token_response.get('status') != 200:
        print(f"    ERROR obteniendo token: {token_response}")
        return

    token = token_response['data'].get('access_token')
    print(f"    Token obtenido: {token[:50]}...")

    # 2. Consultar servicio
    print(f"\n[2] Consultando ubicación para cédula {cedula}...")

    params = {
        'tipoId': '2',
        'numeroId': RECONOCER_CONFIG['NIT'],
        'nit': RECONOCER_CONFIG['NIT'],
        'tipoIdBuscar': '1',
        'numeroIdBuscar': cedula,
        'primerApellidoBuscar': apellido.lower(),
        'validarNombre': 'false',
    }

    query_string = urllib.parse.urlencode(params)
    url = f"{RECONOCER_CONFIG['API_URL']}?{query_string}"

    api_headers = {
        'access_token': token,
        'client_id': RECONOCER_CONFIG['CLIENT_ID'],
        'client_secret': RECONOCER_CONFIG['CLIENT_SECRET'],
        'accept': 'application/json',
    }

    api_response = http_request(url, method='GET', headers=api_headers)

    print(f"\n[3] RESPUESTA (status: {api_response.get('status')}):")
    print("-"*60)

    if api_response.get('error'):
        print(f"ERROR: {api_response.get('error')}")

    data = api_response.get('data')
    if data:
        print(json.dumps(data, indent=2, ensure_ascii=False)[:2000])

    return api_response


def main():
    # Valores por defecto (de las colecciones Postman)
    cedula = '1136415184'
    apellido = 'RUIZ'

    # Parsear argumentos simples
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == '--cedula' and i + 1 < len(args):
            cedula = args[i + 1]
            i += 2
        elif args[i] == '--apellido' and i + 1 < len(args):
            apellido = args[i + 1]
            i += 2
        else:
            i += 1

    print("\n" + "#"*60)
    print("# PRUEBA DE CONEXIÓN DATACREDITO")
    print("#"*60)
    print(f"\nCédula: {cedula}")
    print(f"Apellido: {apellido}")

    # Probar HPN
    test_hpn(cedula, apellido)

    # Probar Reconocer
    test_reconocer(cedula, apellido)

    print("\n" + "#"*60)
    print("# FIN DE PRUEBAS")
    print("#"*60 + "\n")


if __name__ == '__main__':
    main()
