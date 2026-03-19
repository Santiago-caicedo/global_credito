#!/usr/bin/env python3
"""
Genera evidencias de conexión Request/Response para DataCrédito (Experian).
Produce un archivo HTML con la documentación completa del consumo exitoso
de los servicios HPN y Reconocer Master en ambiente de pruebas.

Uso:
    python generar_evidencias_datacredito.py
    python generar_evidencias_datacredito.py --cedula 1136415184 --apellido RUIZ
    python generar_evidencias_datacredito.py --solo-hpn
    python generar_evidencias_datacredito.py --solo-reconocer
"""

import urllib.request
import urllib.parse
import urllib.error
import json
import ssl
import sys
import uuid
from datetime import datetime

# Ignorar verificación SSL para ambiente demo
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# ==============================================================================
# CREDENCIALES (ambiente demo/UAT)
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

# ==============================================================================
# FUNCIONES DE CAPTURA REQUEST/RESPONSE
# ==============================================================================

def http_request_with_evidence(url, method='GET', headers=None, data=None, json_data=None):
    """
    Realiza una petición HTTP y captura toda la evidencia del request y response.
    """
    headers = headers or {}
    raw_body = None

    if json_data:
        raw_body = json.dumps(json_data, indent=2, ensure_ascii=False)
        data = raw_body.encode('utf-8')
        headers['Content-Type'] = 'application/json'
    elif data and isinstance(data, dict):
        raw_body = urllib.parse.urlencode(data)
        data = raw_body.encode('utf-8')
        if 'Content-Type' not in headers:
            headers['Content-Type'] = 'application/x-www-form-urlencoded'

    evidence = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'request': {
            'method': method,
            'url': url,
            'headers': dict(headers),
            'body': raw_body,
        },
        'response': {
            'status': None,
            'headers': {},
            'body': None,
            'body_raw': None,
            'error': None,
        }
    }

    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, context=ssl_context, timeout=60) as response:
            body_raw = response.read().decode('utf-8')
            evidence['response']['status'] = response.status
            evidence['response']['headers'] = dict(response.headers)
            evidence['response']['body_raw'] = body_raw
            try:
                evidence['response']['body'] = json.loads(body_raw)
            except:
                evidence['response']['body'] = body_raw

    except urllib.error.HTTPError as e:
        body_raw = e.read().decode('utf-8') if e.fp else ''
        evidence['response']['status'] = e.code
        evidence['response']['headers'] = dict(e.headers) if e.headers else {}
        evidence['response']['body_raw'] = body_raw
        evidence['response']['error'] = str(e)
        try:
            evidence['response']['body'] = json.loads(body_raw)
        except:
            evidence['response']['body'] = body_raw

    except Exception as e:
        evidence['response']['status'] = 0
        evidence['response']['error'] = str(e)

    return evidence


def mask_sensitive(value, visible_chars=8):
    """Enmascara valores sensibles dejando los primeros caracteres visibles."""
    if not value or len(str(value)) <= visible_chars:
        return str(value)
    return str(value)[:visible_chars] + '*' * (len(str(value)) - visible_chars)


# ==============================================================================
# EJECUCIÓN DE PRUEBAS CON CAPTURA
# ==============================================================================

def ejecutar_hpn(cedula, apellido):
    """Ejecuta la prueba completa de HPN capturando evidencias."""
    print("[HPN] Obteniendo token de acceso...")

    # Paso 1: Token
    token_evidence = http_request_with_evidence(
        url=HPN_CONFIG['TOKEN_URL'],
        method='POST',
        headers={
            'client_id': HPN_CONFIG['CLIENT_ID'],
            'client_secret': HPN_CONFIG['CLIENT_SECRET'],
            'Content-Type': 'application/json',
        },
        json_data={
            'username': HPN_CONFIG['USERNAME'],
            'password': HPN_CONFIG['PASSWORD'],
        }
    )

    token = None
    if token_evidence['response']['body'] and isinstance(token_evidence['response']['body'], dict):
        token = token_evidence['response']['body'].get('access_token')

    if not token:
        print(f"[HPN] ERROR obteniendo token: status {token_evidence['response']['status']}")
        return token_evidence, None

    print(f"[HPN] Token obtenido exitosamente (status {token_evidence['response']['status']})")

    # Paso 2: Consulta API
    print(f"[HPN] Consultando historia de crédito para cédula {cedula}...")

    api_evidence = http_request_with_evidence(
        url=HPN_CONFIG['API_URL'],
        method='POST',
        headers={
            'Content-Type': 'application/json',
            'serverIpAddress': HPN_CONFIG['SERVER_IP'],
            'ProductId': HPN_CONFIG['PRODUCT_ID'],
            'InfoAccountType': '1',
            'client_id': HPN_CONFIG['CLIENT_ID'],
            'client_secret': HPN_CONFIG['CLIENT_SECRET'],
            'Authorization': f'Bearer {token}',
        },
        json_data={
            'user': HPN_CONFIG['USER'],
            'password': HPN_CONFIG['USER_PASSWORD'],
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
                        'personIdType': 1,
                    },
                    'personLastName': apellido.upper(),
                }
            }
        }
    )

    print(f"[HPN] Respuesta recibida (status {api_evidence['response']['status']})")
    return token_evidence, api_evidence


def ejecutar_reconocer(cedula, apellido):
    """Ejecuta la prueba completa de Reconocer capturando evidencias."""
    print("\n[RECONOCER] Obteniendo token de acceso Okta...")

    # Paso 1: Token
    token_evidence = http_request_with_evidence(
        url=RECONOCER_CONFIG['TOKEN_URL'],
        method='POST',
        headers={
            'Authorization': RECONOCER_CONFIG['AUTHORIZATION'],
            'accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        data={
            'grant_type': 'password',
            'username': RECONOCER_CONFIG['USERNAME'],
            'password': RECONOCER_CONFIG['PASSWORD'],
            'scope': RECONOCER_CONFIG['SCOPE'],
        }
    )

    token = None
    if token_evidence['response']['body'] and isinstance(token_evidence['response']['body'], dict):
        token = token_evidence['response']['body'].get('access_token')

    if not token:
        print(f"[RECONOCER] ERROR obteniendo token: status {token_evidence['response']['status']}")
        return token_evidence, None

    print(f"[RECONOCER] Token obtenido exitosamente (status {token_evidence['response']['status']})")

    # Paso 2: Consulta API
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

    print(f"[RECONOCER] Consultando ubicación para cédula {cedula}...")

    api_evidence = http_request_with_evidence(
        url=url,
        method='GET',
        headers={
            'access_token': token,
            'client_id': RECONOCER_CONFIG['CLIENT_ID'],
            'client_secret': RECONOCER_CONFIG['CLIENT_SECRET'],
            'accept': 'application/json',
        }
    )

    print(f"[RECONOCER] Respuesta recibida (status {api_evidence['response']['status']})")
    return token_evidence, api_evidence


# ==============================================================================
# GENERACIÓN DEL HTML DE EVIDENCIAS
# ==============================================================================

def generar_html_evidencias(evidencias, cedula, apellido, empresa_info):
    """Genera el HTML completo con las evidencias."""

    fecha_generacion = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def format_json(obj):
        """Formatea JSON con indentación para el HTML."""
        if obj is None:
            return '<span style="color:#999;">null</span>'
        if isinstance(obj, str):
            try:
                obj = json.loads(obj)
            except:
                return obj
        return json.dumps(obj, indent=2, ensure_ascii=False)

    def render_headers(headers, mask_secrets=True):
        """Renderiza headers como tabla."""
        if not headers:
            return '<em>Sin headers</em>'

        # Headers que contienen secretos
        secret_keys = {'client_secret', 'authorization', 'access_token'}

        rows = ''
        for k, v in headers.items():
            display_val = v
            if mask_secrets and k.lower() in secret_keys:
                display_val = mask_sensitive(str(v), 20)
            rows += f'<tr><td class="header-key">{k}</td><td class="header-val">{display_val}</td></tr>\n'
        return f'<table class="headers-table"><tbody>{rows}</tbody></table>'

    def render_evidence_block(title, ev, mask_secrets=True):
        """Renderiza un bloque completo de request/response."""
        if ev is None:
            return f'''
            <div class="evidence-block">
                <h3>{title}</h3>
                <div class="error-box">No se ejecutó esta consulta (paso anterior falló)</div>
            </div>'''

        req = ev['request']
        res = ev['response']

        status_class = 'status-ok' if res['status'] and 200 <= res['status'] < 300 else 'status-error'

        # Request body
        req_body_html = ''
        if req['body']:
            body_display = req['body']
            if mask_secrets:
                try:
                    body_obj = json.loads(req['body']) if isinstance(req['body'], str) else req['body']
                    if isinstance(body_obj, dict):
                        for key in ['password', 'client_secret']:
                            if key in body_obj:
                                body_obj[key] = mask_sensitive(str(body_obj[key]), 4)
                        body_display = json.dumps(body_obj, indent=2, ensure_ascii=False)
                except:
                    pass
            req_body_html = f'<pre class="json-block">{body_display}</pre>'
        else:
            req_body_html = '<em>Sin body</em>'

        # Response body
        res_body_html = ''
        if res.get('error') and not res.get('body'):
            res_body_html = f'<div class="error-box">{res["error"]}</div>'
        elif res['body']:
            res_body_html = f'<pre class="json-block">{format_json(res["body"])}</pre>'
        else:
            res_body_html = '<em>Sin body</em>'

        return f'''
        <div class="evidence-block">
            <h3>{title}</h3>
            <p class="timestamp">Fecha/hora de ejecución: <strong>{ev['timestamp']}</strong></p>

            <div class="section">
                <h4>REQUEST</h4>
                <div class="method-url">
                    <span class="method">{req['method']}</span>
                    <span class="url">{req['url']}</span>
                </div>

                <h5>Headers</h5>
                {render_headers(req['headers'], mask_secrets)}

                <h5>Body</h5>
                {req_body_html}
            </div>

            <div class="section">
                <h4>RESPONSE</h4>
                <div class="status-line">
                    HTTP Status: <span class="{status_class}">{res['status']}</span>
                </div>

                <h5>Headers</h5>
                {render_headers(res.get('headers', {}), False)}

                <h5>Body</h5>
                {res_body_html}
            </div>
        </div>'''

    # Construir secciones
    sections_html = ''

    for evidencia in evidencias:
        nombre_api = evidencia['api']
        token_ev = evidencia.get('token')
        api_ev = evidencia.get('api_call')

        sections_html += f'''
        <div class="api-section">
            <h2>{nombre_api}</h2>
            {render_evidence_block("Paso 1: Autenticación (OAuth2 Token)", token_ev)}
            {render_evidence_block("Paso 2: Consumo del Servicio", api_ev)}
        </div>
        '''

    html = f'''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Evidencias de Conexión DataCrédito - {empresa_info['nombre']}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #f5f5f5;
            color: #333;
            line-height: 1.6;
        }}
        .container {{
            max-width: 1100px;
            margin: 0 auto;
            padding: 20px;
        }}

        /* Header */
        .doc-header {{
            background: linear-gradient(135deg, #4d5572 0%, #7a87a5 100%);
            color: white;
            padding: 30px 40px;
            border-radius: 8px 8px 0 0;
            margin-bottom: 0;
        }}
        .doc-header h1 {{
            font-size: 24px;
            margin-bottom: 5px;
        }}
        .doc-header .subtitle {{
            font-size: 16px;
            opacity: 0.9;
        }}
        .doc-header .empresa {{
            margin-top: 15px;
            font-size: 14px;
            opacity: 0.85;
        }}

        /* Info box */
        .info-box {{
            background: white;
            padding: 20px 40px;
            border: 1px solid #ddd;
            border-top: none;
            margin-bottom: 20px;
            border-radius: 0 0 8px 8px;
        }}
        .info-box table {{
            width: 100%;
        }}
        .info-box td {{
            padding: 4px 10px;
            vertical-align: top;
        }}
        .info-box td:first-child {{
            font-weight: 600;
            color: #4d5572;
            width: 220px;
        }}

        /* API sections */
        .api-section {{
            margin-bottom: 30px;
        }}
        .api-section h2 {{
            background: #4d5572;
            color: white;
            padding: 12px 20px;
            border-radius: 6px 6px 0 0;
            font-size: 18px;
        }}

        /* Evidence blocks */
        .evidence-block {{
            background: white;
            border: 1px solid #ddd;
            border-top: none;
            padding: 20px;
            margin-bottom: 0;
        }}
        .evidence-block:last-child {{
            border-radius: 0 0 6px 6px;
        }}
        .evidence-block h3 {{
            color: #4d5572;
            font-size: 16px;
            margin-bottom: 10px;
            padding-bottom: 5px;
            border-bottom: 2px solid #a3b38d;
        }}
        .timestamp {{
            color: #666;
            font-size: 13px;
            margin-bottom: 15px;
        }}

        /* Sections */
        .section {{
            margin: 15px 0;
            padding: 15px;
            background: #fafafa;
            border-radius: 4px;
            border: 1px solid #eee;
        }}
        .section h4 {{
            color: #4d5572;
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 10px;
        }}
        .section h5 {{
            color: #666;
            font-size: 13px;
            margin: 10px 0 5px;
        }}

        /* Method + URL */
        .method-url {{
            background: #2d2d2d;
            color: #f8f8f2;
            padding: 10px 15px;
            border-radius: 4px;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 13px;
            word-break: break-all;
        }}
        .method {{
            background: #a3b38d;
            color: white;
            padding: 2px 8px;
            border-radius: 3px;
            font-weight: bold;
            margin-right: 10px;
        }}

        /* Headers table */
        .headers-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 12px;
            font-family: 'Consolas', 'Monaco', monospace;
        }}
        .headers-table td {{
            padding: 4px 8px;
            border-bottom: 1px solid #eee;
            vertical-align: top;
        }}
        .header-key {{
            color: #4d5572;
            font-weight: 600;
            width: 250px;
            white-space: nowrap;
        }}
        .header-val {{
            color: #555;
            word-break: break-all;
        }}

        /* JSON block */
        .json-block {{
            background: #2d2d2d;
            color: #f8f8f2;
            padding: 15px;
            border-radius: 4px;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 12px;
            overflow-x: auto;
            white-space: pre-wrap;
            word-wrap: break-word;
            max-height: 600px;
            overflow-y: auto;
        }}

        /* Status */
        .status-line {{
            font-size: 14px;
            margin-bottom: 10px;
        }}
        .status-ok {{
            background: #a3b38d;
            color: white;
            padding: 2px 12px;
            border-radius: 3px;
            font-weight: bold;
        }}
        .status-error {{
            background: #e74c3c;
            color: white;
            padding: 2px 12px;
            border-radius: 3px;
            font-weight: bold;
        }}

        /* Error box */
        .error-box {{
            background: #fff3cd;
            border: 1px solid #ffc107;
            color: #856404;
            padding: 10px 15px;
            border-radius: 4px;
        }}

        /* Footer */
        .doc-footer {{
            text-align: center;
            color: #999;
            font-size: 12px;
            margin-top: 30px;
            padding: 20px;
        }}

        /* Print styles */
        @media print {{
            body {{ background: white; }}
            .container {{ max-width: 100%; padding: 0; }}
            .json-block {{ max-height: none; }}
            .evidence-block, .api-section {{ page-break-inside: avoid; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="doc-header">
            <h1>Evidencias de Conexión - Web Services DataCrédito</h1>
            <div class="subtitle">Request y Response - Ambiente de Pruebas (UAT/Demo)</div>
            <div class="empresa">{empresa_info['nombre']} | NIT: {empresa_info['nit']}</div>
        </div>

        <div class="info-box">
            <table>
                <tr>
                    <td>Fecha de generación:</td>
                    <td>{fecha_generacion}</td>
                </tr>
                <tr>
                    <td>Ambiente:</td>
                    <td>Demo / UAT (pruebas)</td>
                </tr>
                <tr>
                    <td>Empresa suscriptora:</td>
                    <td>{empresa_info['nombre']}</td>
                </tr>
                <tr>
                    <td>NIT:</td>
                    <td>{empresa_info['nit']}</td>
                </tr>
                <tr>
                    <td>Cédula consultada:</td>
                    <td>{cedula}</td>
                </tr>
                <tr>
                    <td>Apellido consultado:</td>
                    <td>{apellido}</td>
                </tr>
                <tr>
                    <td>IP del servidor:</td>
                    <td>{HPN_CONFIG['SERVER_IP']}</td>
                </tr>
            </table>
        </div>

        {sections_html}

        <div class="doc-footer">
            Documento generado automáticamente como evidencia de consumo exitoso de servicios web.<br>
            {empresa_info['nombre']} — {fecha_generacion}
        </div>
    </div>
</body>
</html>'''

    return html


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    cedula = '1136415184'
    apellido = 'RUIZ'
    solo_hpn = False
    solo_reconocer = False

    # Parsear argumentos
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == '--cedula' and i + 1 < len(args):
            cedula = args[i + 1]
            i += 2
        elif args[i] == '--apellido' and i + 1 < len(args):
            apellido = args[i + 1]
            i += 2
        elif args[i] == '--solo-hpn':
            solo_hpn = True
            i += 1
        elif args[i] == '--solo-reconocer':
            solo_reconocer = True
            i += 1
        else:
            i += 1

    empresa_info = {
        'nombre': 'Global Care Financial Services S.A.S.',
        'nit': '901290934',
    }

    print("=" * 60)
    print("GENERADOR DE EVIDENCIAS DATACREDITO")
    print("=" * 60)
    print(f"Cédula: {cedula}")
    print(f"Apellido: {apellido}")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    evidencias = []

    # HPN
    if not solo_reconocer:
        print("\n>>> Ejecutando API HPN...")
        hpn_token_ev, hpn_api_ev = ejecutar_hpn(cedula, apellido)
        evidencias.append({
            'api': 'API HPN REST — Historia de Crédito + Advance Score (Z0) + Quanto (O4)',
            'token': hpn_token_ev,
            'api_call': hpn_api_ev,
        })

    # Reconocer
    if not solo_hpn:
        print("\n>>> Ejecutando API Reconocer Master...")
        rec_token_ev, rec_api_ev = ejecutar_reconocer(cedula, apellido)
        evidencias.append({
            'api': 'API Reconocer Master — Ubicación + Contacto + Identidad',
            'token': rec_token_ev,
            'api_call': rec_api_ev,
        })

    # Generar HTML
    print("\n>>> Generando documento de evidencias...")
    html = generar_html_evidencias(evidencias, cedula, apellido, empresa_info)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'evidencias_datacredito_{timestamp}.html'
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"\n{'=' * 60}")
    print(f"EVIDENCIAS GENERADAS EXITOSAMENTE")
    print(f"{'=' * 60}")
    print(f"Archivo: {filename}")
    print(f"\nAbra el archivo en un navegador para visualizar las evidencias.")
    print(f"Puede guardarlo como PDF desde el navegador (Ctrl+P > Guardar como PDF).")
    print(f"{'=' * 60}\n")


if __name__ == '__main__':
    main()
