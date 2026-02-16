# creditos/management/commands/test_datacredito.py
"""
Comando para probar la conexion con DataCredito.

Uso:
    python manage.py test_datacredito                    # Usa datos de ejemplo
    python manage.py test_datacredito --cedula 123456 --apellido PEREZ
    python manage.py test_datacredito --solo-hpn         # Solo prueba HPN
    python manage.py test_datacredito --solo-reconocer   # Solo prueba Reconocer
"""

from django.core.management.base import BaseCommand
from creditos.datacredito_service import (
    DataCreditoHPNClient,
    DataCreditoReconocerClient,
)
import json


class Command(BaseCommand):
    help = 'Prueba la conexion con las APIs de DataCredito (HPN y Reconocer)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--cedula',
            type=str,
            default='1136415184',  # Dato de ejemplo de la coleccion Postman
            help='Numero de cedula a consultar (default: 1136415184)'
        )
        parser.add_argument(
            '--apellido',
            type=str,
            default='RUIZ',  # Dato de ejemplo de la coleccion Postman
            help='Primer apellido (default: RUIZ)'
        )
        parser.add_argument(
            '--solo-hpn',
            action='store_true',
            help='Solo probar API HPN (Historia de Credito)'
        )
        parser.add_argument(
            '--solo-reconocer',
            action='store_true',
            help='Solo probar API Reconocer Master'
        )

    def handle(self, *args, **options):
        cedula = options['cedula']
        apellido = options['apellido']
        solo_hpn = options['solo_hpn']
        solo_reconocer = options['solo_reconocer']

        self.stdout.write(self.style.WARNING(
            f'\n{"="*60}\n'
            f'PRUEBA DE CONEXION DATACREDITO\n'
            f'{"="*60}\n'
            f'Cedula: {cedula}\n'
            f'Apellido: {apellido}\n'
            f'{"="*60}\n'
        ))

        # Probar HPN
        if not solo_reconocer:
            self._test_hpn(cedula, apellido)

        # Probar Reconocer
        if not solo_hpn:
            self._test_reconocer(cedula, apellido)

    def _test_hpn(self, cedula, apellido):
        self.stdout.write(self.style.HTTP_INFO(
            '\n--- API HPN (Historia de Credito + Score + Quanto) ---\n'
        ))

        client = DataCreditoHPNClient()

        if not client.enabled:
            self.stdout.write(self.style.WARNING(
                'API HPN DESHABILITADA. Activa DATACREDITO_HPN_ENABLED=True en .env'
            ))
            return

        self.stdout.write('Obteniendo token...')
        try:
            resultado = client.consultar(cedula, apellido)

            if resultado.get('success'):
                self.stdout.write(self.style.SUCCESS('\nCONSULTA EXITOSA'))
                self._mostrar_resultado_hpn(resultado)
            else:
                self.stdout.write(self.style.ERROR(
                    f'\nERROR: {resultado.get("error", "Error desconocido")}'
                ))
                self.stdout.write(f'Codigo: {resultado.get("codigo")}')

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\nEXCEPCION: {str(e)}'))

    def _test_reconocer(self, cedula, apellido):
        self.stdout.write(self.style.HTTP_INFO(
            '\n--- API RECONOCER MASTER (Ubicacion + Contacto) ---\n'
        ))

        client = DataCreditoReconocerClient()

        if not client.enabled:
            self.stdout.write(self.style.WARNING(
                'API RECONOCER DESHABILITADA. Activa DATACREDITO_RECONOCER_ENABLED=True en .env'
            ))
            return

        self.stdout.write('Obteniendo token...')
        try:
            resultado = client.consultar(cedula, apellido)

            if resultado.get('success'):
                self.stdout.write(self.style.SUCCESS('\nCONSULTA EXITOSA'))
                self._mostrar_resultado_reconocer(resultado)
            else:
                self.stdout.write(self.style.ERROR(
                    f'\nERROR: {resultado.get("error", "Error desconocido")}'
                ))
                self.stdout.write(f'Codigo: {resultado.get("codigo")}')

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\nEXCEPCION: {str(e)}'))

    def _mostrar_resultado_hpn(self, resultado):
        self.stdout.write(f'\nCodigo respuesta: {resultado.get("codigo")}')
        self.stdout.write(f'Mensaje: {resultado.get("mensaje")}')

        self.stdout.write(self.style.WARNING('\n-- SCORE --'))
        self.stdout.write(f'Advance Score (Z0): {resultado.get("advance_score")}')
        self.stdout.write(f'Descripcion: {resultado.get("score_descripcion")}')

        self.stdout.write(self.style.WARNING('\n-- QUANTO (Patrimonio) --'))
        self.stdout.write(f'Valor estimado: ${resultado.get("quanto_valor"):,.0f}' if resultado.get("quanto_valor") else 'No disponible')

        self.stdout.write(self.style.WARNING('\n-- CARTERA --'))
        self.stdout.write(f'Total obligaciones: {resultado.get("total_obligaciones")}')
        self.stdout.write(f'Al dia: {resultado.get("obligaciones_al_dia")}')
        self.stdout.write(f'En mora: {resultado.get("obligaciones_mora")}')
        self.stdout.write(f'Saldo total: ${resultado.get("saldo_total"):,.0f}' if resultado.get("saldo_total") else 'N/A')
        self.stdout.write(f'Saldo en mora: ${resultado.get("saldo_mora"):,.0f}' if resultado.get("saldo_mora") else 'N/A')
        self.stdout.write(f'Cuota mensual: ${resultado.get("cuota_mensual_total"):,.0f}' if resultado.get("cuota_mensual_total") else 'N/A')

        self.stdout.write(self.style.WARNING('\n-- MORAS POR SECTOR --'))
        self.stdout.write(f'Mora Telco: ${resultado.get("mora_telco"):,.0f}' if resultado.get("mora_telco") else '$0')
        self.stdout.write(f'Mora Sector Real: ${resultado.get("mora_sector_real"):,.0f}' if resultado.get("mora_sector_real") else '$0')
        self.stdout.write(f'Mora Sector Financiero: ${resultado.get("mora_sector_financiero"):,.0f}' if resultado.get("mora_sector_financiero") else '$0')

        self.stdout.write(self.style.WARNING('\n-- HUELLAS --'))
        self.stdout.write(f'Consultas ultimos 6 meses: {resultado.get("huellas_ultimos_6_meses")}')

        # Vector de comportamiento (resumido)
        vector = resultado.get('vector_comportamiento', [])
        if vector:
            self.stdout.write(self.style.WARNING('\n-- COMPORTAMIENTO DE PAGO (primeras 3 cuentas) --'))
            for cuenta in vector[:3]:
                historial = cuenta.get('historial', [])[:12]  # Ultimos 12 meses
                historial_str = ''.join(str(h) if h else '-' for h in historial)
                self.stdout.write(f'{cuenta.get("entidad", "N/A")[:30]}: {historial_str}')

    def _mostrar_resultado_reconocer(self, resultado):
        self.stdout.write(f'\nCodigo respuesta: {resultado.get("codigo")}')
        self.stdout.write(f'Mensaje: {resultado.get("mensaje")}')

        self.stdout.write(self.style.WARNING('\n-- UBICACION --'))
        self.stdout.write(f'Ciudad: {resultado.get("ciudad")}')
        self.stdout.write(f'Departamento: {resultado.get("departamento")}')
        self.stdout.write(f'Direccion: {resultado.get("direccion")}')
        self.stdout.write(f'Estrato: {resultado.get("estrato")}')

        self.stdout.write(self.style.WARNING('\n-- CONTACTO --'))
        self.stdout.write(f'Telefono: {resultado.get("telefono")}')
        self.stdout.write(f'Celular: {resultado.get("celular")}')
        self.stdout.write(f'Email: {resultado.get("email")}')
