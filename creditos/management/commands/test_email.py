from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings


class Command(BaseCommand):
    help = 'Envia un email de prueba para verificar la configuracion SMTP'

    def add_arguments(self, parser):
        parser.add_argument(
            'destinatario',
            type=str,
            help='Email de destino para la prueba'
        )

    def handle(self, *args, **options):
        destinatario = options['destinatario']

        self.stdout.write(self.style.WARNING('Configuracion actual:'))
        self.stdout.write(f'  EMAIL_BACKEND: {settings.EMAIL_BACKEND}')
        self.stdout.write(f'  EMAIL_HOST: {settings.EMAIL_HOST}')
        self.stdout.write(f'  EMAIL_PORT: {settings.EMAIL_PORT}')
        self.stdout.write(f'  EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}')
        self.stdout.write(f'  EMAIL_USE_SSL: {settings.EMAIL_USE_SSL}')
        self.stdout.write(f'  EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}')
        self.stdout.write(f'  DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}')
        self.stdout.write('')

        self.stdout.write(self.style.WARNING(f'Enviando email de prueba a: {destinatario}'))

        try:
            send_mail(
                subject='Prueba de Email - Global Care F.S.',
                message='Este es un email de prueba del sistema de creditos de Global Care Financial Services.\n\nSi recibes este mensaje, la configuracion de email esta funcionando correctamente.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[destinatario],
                fail_silently=False,
            )
            self.stdout.write(self.style.SUCCESS(f'Email enviado exitosamente a {destinatario}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error al enviar email: {e}'))
