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
max_requests = 1000  # reciclar workers cada 1000 requests
max_requests_jitter = 50

# Timeouts
timeout = 120  # 2 minutos para requests lentos
keepalive = 5  # mantener conexiones HTTP activas
graceful_timeout = 30

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

# Preload app para ahorrar memoria
preload_app = True

# Hooks para cerrar conexiones DB antes de reciclar workers
def worker_exit(server, worker):
    """Cerrar conexiones DB cuando un worker termina"""
    from django.db import connections
    connections.close_all()

def on_exit(server):
    """Cerrar conexiones DB cuando el servidor termina"""
    from django.db import connections
    connections.close_all()
