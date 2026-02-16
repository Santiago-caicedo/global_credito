from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from usuarios.models import PerfilUsuario


class Command(BaseCommand):
    help = 'Crea usuarios de prueba para Analista y Director'

    def handle(self, *args, **options):
        # Crear Analista
        if not User.objects.filter(username='analista').exists():
            analista = User.objects.create_user(
                username='analista',
                email='analista@globalcare.com',
                password='Analista123',
                first_name='Ana',
                last_name='Garcia'
            )
            PerfilUsuario.objects.create(
                user=analista,
                rol='ANALISTA',
                telefono='3001234567'
            )
            self.stdout.write(self.style.SUCCESS('Usuario ANALISTA creado'))
        else:
            self.stdout.write(self.style.WARNING('Usuario ANALISTA ya existe'))

        # Crear Director
        if not User.objects.filter(username='director').exists():
            director = User.objects.create_user(
                username='director',
                email='director@globalcare.com',
                password='Director123',
                first_name='Carlos',
                last_name='Martinez'
            )
            PerfilUsuario.objects.create(
                user=director,
                rol='DIRECTOR',
                telefono='3009876543'
            )
            self.stdout.write(self.style.SUCCESS('Usuario DIRECTOR creado'))
        else:
            self.stdout.write(self.style.WARNING('Usuario DIRECTOR ya existe'))

        self.stdout.write('')
        self.stdout.write(self.style.HTTP_INFO('--- Credenciales de Prueba ---'))
        self.stdout.write('ANALISTA:')
        self.stdout.write('  Usuario: analista')
        self.stdout.write('  Password: Analista123')
        self.stdout.write('')
        self.stdout.write('DIRECTOR:')
        self.stdout.write('  Usuario: director')
        self.stdout.write('  Password: Director123')
