# Gunicorn configuration file
# Optimizado para Render free tier + Supabase Transaction Pooler

import os
import multiprocessing

# Server socket
bind = f"0.0.0.0:{os.getenv('PORT', '10000')}"
backlog = 2048

# Worker processes
# En free tier de Render, limitar workers para no exceder memoria
workers = int(os.getenv('WEB_CONCURRENCY', 2))
worker_class = 'sync'
threads = 4  # threads por worker
worker_connections = 1000
max_requests = 500  # reciclar workers más frecuentemente
max_requests_jitter = 100

# Timeouts
timeout = 180  # 3 minutos para requests lentos (aumentado)
keepalive = 2  # mantener conexiones HTTP activas (reducido para liberar más rápido)
graceful_timeout = 60

# Logging
accesslog = '-'  # stdout
errorlog = '-'   # stderr
loglevel = 'info'
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = 'smartsales_gunicorn'

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# NO preload app - permite que cada worker maneje su propia conexión DB
preload_app = False

# Hooks para manejar workers y conexiones DB
def pre_fork(server, worker):
    """Antes de hacer fork de un nuevo worker"""
    pass

def post_fork(server, worker):
    """Después de hacer fork de un nuevo worker"""
    # Cerrar todas las conexiones DB heredadas del proceso padre
    from django.db import connections
    connections.close_all()

def worker_int(worker):
    """Cuando un worker recibe SIGINT"""
    from django.db import connections
    connections.close_all()

def worker_exit(server, worker):
    """Cerrar conexiones DB cuando un worker termina"""
    from django.db import connections
    connections.close_all()

def on_exit(server):
    """Cerrar conexiones DB cuando el servidor termina"""
    from django.db import connections
    connections.close_all()

def when_ready(server):
    """Cuando el servidor está listo"""
    print("🚀 Gunicorn is ready. Listening on: " + bind)
