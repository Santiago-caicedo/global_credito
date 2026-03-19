from django.core.management.base import BaseCommand
from creditos.models import SolicitudCredito, ConsultaDataCredito
from decimal import Decimal


# Perfiles de prueba con datos realistas
PERFILES = {
    'bueno': {
        'descripcion': 'Cliente con buen perfil crediticio',
        'hpn': {
            'advance_score': 720,
            'score_descripcion': 'Riesgo bajo',
            'quanto_valor': Decimal('62000000'),
            'total_obligaciones': 4,
            'obligaciones_al_dia': 4,
            'obligaciones_mora': 0,
            'saldo_total': Decimal('8500000'),
            'saldo_mora': Decimal('0'),
            'cuota_mensual_total': Decimal('620000'),
            'mora_telco': Decimal('0'),
            'mora_sector_real': Decimal('0'),
            'mora_sector_financiero': Decimal('0'),
            'huellas_ultimos_6_meses': 1,
        },
        'reconocer': {
            'reconocer_ciudad': 'BOGOTA D.C.',
            'reconocer_departamento': 'CUNDINAMARCA',
            'reconocer_direccion': 'CRA 15 # 85-42 APTO 302',
            'reconocer_estrato': '4',
            'reconocer_telefono': '6012345678',
            'reconocer_celular': '3101234567',
            'reconocer_email': 'cliente.bueno@email.com',
        },
    },
    'medio': {
        'descripcion': 'Cliente con perfil medio, algunas alertas',
        'hpn': {
            'advance_score': 480,
            'score_descripcion': 'Riesgo medio',
            'quanto_valor': Decimal('28000000'),
            'total_obligaciones': 7,
            'obligaciones_al_dia': 5,
            'obligaciones_mora': 2,
            'saldo_total': Decimal('15200000'),
            'saldo_mora': Decimal('1800000'),
            'cuota_mensual_total': Decimal('1150000'),
            'mora_telco': Decimal('180000'),
            'mora_sector_real': Decimal('250000'),
            'mora_sector_financiero': Decimal('320000'),
            'huellas_ultimos_6_meses': 3,
        },
        'reconocer': {
            'reconocer_ciudad': 'MEDELLIN',
            'reconocer_departamento': 'ANTIOQUIA',
            'reconocer_direccion': 'CL 45 # 70-12 INT 201',
            'reconocer_estrato': '3',
            'reconocer_telefono': '6044567890',
            'reconocer_celular': '3209876543',
            'reconocer_email': 'cliente.medio@email.com',
        },
    },
    'malo': {
        'descripcion': 'Cliente de alto riesgo (seria rechazado automaticamente)',
        'hpn': {
            'advance_score': 230,
            'score_descripcion': 'Riesgo muy alto',
            'quanto_valor': Decimal('5000000'),
            'total_obligaciones': 12,
            'obligaciones_al_dia': 3,
            'obligaciones_mora': 9,
            'saldo_total': Decimal('42000000'),
            'saldo_mora': Decimal('18500000'),
            'cuota_mensual_total': Decimal('2800000'),
            'mora_telco': Decimal('450000'),
            'mora_sector_real': Decimal('3200000'),
            'mora_sector_financiero': Decimal('8700000'),
            'huellas_ultimos_6_meses': 7,
        },
        'reconocer': {
            'reconocer_ciudad': 'CALI',
            'reconocer_departamento': 'VALLE DEL CAUCA',
            'reconocer_direccion': 'AV 3N # 28-45',
            'reconocer_estrato': '2',
            'reconocer_telefono': '6023456789',
            'reconocer_celular': '3158765432',
            'reconocer_email': 'cliente.riesgo@email.com',
        },
    },
}


class Command(BaseCommand):
    help = 'Pobla los registros de ConsultaDataCredito con datos realistas de prueba'

    def add_arguments(self, parser):
        parser.add_argument(
            '--solicitud',
            type=int,
            help='ID de la solicitud a poblar. Si no se indica, usa la mas reciente.',
        )
        parser.add_argument(
            '--perfil',
            type=str,
            default='bueno',
            choices=['bueno', 'medio', 'malo'],
            help='Perfil de riesgo a simular (default: bueno)',
        )
        parser.add_argument(
            '--listar',
            action='store_true',
            help='Lista las solicitudes disponibles y sale',
        )

    def handle(self, *args, **options):
        # Modo listar
        if options['listar']:
            solicitudes = SolicitudCredito.objects.all().order_by('-fecha_creacion')[:10]
            if not solicitudes:
                self.stdout.write(self.style.WARNING('No hay solicitudes en la base de datos.'))
                return

            self.stdout.write(self.style.HTTP_INFO('\n--- Ultimas 10 solicitudes ---'))
            for s in solicitudes:
                consultas = s.consultas_datacredito.count()
                self.stdout.write(
                    f'  #{s.id} | {s.cedula} | {s.nombre_completo} | '
                    f'{s.get_estado_display()} | Consultas DC: {consultas}'
                )
            self.stdout.write('')
            return

        # Buscar solicitud
        if options['solicitud']:
            try:
                solicitud = SolicitudCredito.objects.get(id=options['solicitud'])
            except SolicitudCredito.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'No existe solicitud con ID #{options["solicitud"]}'))
                return
        else:
            solicitud = SolicitudCredito.objects.order_by('-fecha_creacion').first()
            if not solicitud:
                self.stdout.write(self.style.ERROR('No hay solicitudes en la base de datos. Primero aplica en /aplicar/'))
                return

        perfil_key = options['perfil']
        perfil = PERFILES[perfil_key]

        self.stdout.write(self.style.HTTP_INFO(f'\n--- Poblando DataCredito para Solicitud #{solicitud.id} ---'))
        self.stdout.write(f'  Cliente: {solicitud.nombre_completo} (CC {solicitud.cedula})')
        self.stdout.write(f'  Estado: {solicitud.get_estado_display()}')
        self.stdout.write(f'  Perfil: {perfil_key.upper()} - {perfil["descripcion"]}')
        self.stdout.write('')

        # Actualizar o crear consulta HPN
        hpn_data = perfil['hpn']
        hpn, created = ConsultaDataCredito.objects.update_or_create(
            solicitud=solicitud,
            tipo_consulta='HPN',
            defaults={
                'estado_consulta': ConsultaDataCredito.ESTADO_EXITO,
                'codigo_respuesta': '13',
                'mensaje_respuesta': 'Consulta exitosa con datos (simulado)',
                **hpn_data,
            }
        )
        action = 'Creado' if created else 'Actualizado'
        self.stdout.write(self.style.SUCCESS(
            f'  [HPN] {action} | Score: {hpn_data["advance_score"]} '
            f'({hpn_data["score_descripcion"]}) | '
            f'Moras: Telco ${hpn_data["mora_telco"]:,.0f}, '
            f'Real ${hpn_data["mora_sector_real"]:,.0f}, '
            f'Financiero ${hpn_data["mora_sector_financiero"]:,.0f} | '
            f'Huellas: {hpn_data["huellas_ultimos_6_meses"]}'
        ))

        # Actualizar o crear consulta Reconocer
        rec_data = perfil['reconocer']
        rec, created = ConsultaDataCredito.objects.update_or_create(
            solicitud=solicitud,
            tipo_consulta='RECONOCER',
            defaults={
                'estado_consulta': ConsultaDataCredito.ESTADO_EXITO,
                'codigo_respuesta': '13',
                'mensaje_respuesta': 'Consulta exitosa con datos (simulado)',
                **rec_data,
            }
        )
        action = 'Creado' if created else 'Actualizado'
        self.stdout.write(self.style.SUCCESS(
            f'  [REC] {action} | {rec_data["reconocer_ciudad"]}, '
            f'{rec_data["reconocer_departamento"]} | '
            f'Estrato {rec_data["reconocer_estrato"]} | '
            f'Cel: {rec_data["reconocer_celular"]}'
        ))

        self.stdout.write(self.style.HTTP_INFO(
            f'\nListo. Ingresa como analista o director para ver los datos en la card.'
        ))
