"""
Comando para procesar la cola de notificaciones pendientes
Uso: python manage.py procesar_notificaciones
"""
import logging
from django.core.management.base import BaseCommand
from smartsales.notificaciones.processor import NotificacionProcessor

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Procesa las notificaciones pendientes en la cola'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limite',
            type=int,
            default=100,
            help='Número máximo de notificaciones a procesar (default: 100)'
        )
        parser.add_argument(
            '--continuo',
            action='store_true',
            help='Ejecuta el procesamiento en modo continuo cada cierto tiempo'
        )
        parser.add_argument(
            '--intervalo',
            type=int,
            default=8,
            help='Intervalo en segundos entre ejecuciones en modo continuo (default: 8)'
        )

    def handle(self, *args, **options):
        limite = options['limite']
        continuo = options['continuo']
        intervalo = options['intervalo']
        
        processor = NotificacionProcessor()
        
        if continuo:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Iniciando procesamiento continuo cada {intervalo} segundos...'
                )
            )
            self.stdout.write(self.style.WARNING('Presiona Ctrl+C para detener'))
            
            import time
            try:
                while True:
                    self.stdout.write(
                        self.style.NOTICE(
                            f'\n[{self._get_timestamp()}] Procesando notificaciones...'
                        )
                    )
                    stats = processor.procesar_cola(limite=limite)
                    self._mostrar_estadisticas(stats)
                    
                    self.stdout.write(
                        self.style.NOTICE(
                            f'Esperando {intervalo} segundos para el próximo ciclo...'
                        )
                    )
                    time.sleep(intervalo)
                    
            except KeyboardInterrupt:
                self.stdout.write(
                    self.style.WARNING('\n\nProcesamiento detenido por el usuario')
                )
        else:
            self.stdout.write(
                self.style.SUCCESS('Procesando cola de notificaciones...')
            )
            stats = processor.procesar_cola(limite=limite)
            self._mostrar_estadisticas(stats)
            self.stdout.write(
                self.style.SUCCESS('\n✓ Procesamiento completado')
            )

    def _mostrar_estadisticas(self, stats):
        """Muestra las estadísticas del procesamiento"""
        self.stdout.write('')
        self.stdout.write(f"  Procesadas:   {stats['procesadas']}")
        self.stdout.write(
            self.style.SUCCESS(f"  ✓ Exitosas:   {stats['exitosas']}")
        )
        if stats['reintentadas'] > 0:
            self.stdout.write(
                self.style.WARNING(f"  ⟳ Reintentadas: {stats['reintentadas']}")
            )
        if stats['fallidas'] > 0:
            self.stdout.write(
                self.style.ERROR(f"  ✗ Fallidas:   {stats['fallidas']}")
            )

    def _get_timestamp(self):
        """Retorna timestamp actual formateado"""
        from datetime import datetime
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
