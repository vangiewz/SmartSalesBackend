"""
Utilidades para manejar conexiones de BD con retry logic.
Útil para Supabase Transaction Pooler en free tier.
"""
from django.db import connection
from django.db.utils import OperationalError, InterfaceError, DatabaseError
from functools import wraps
import time
import logging

logger = logging.getLogger(__name__)


def db_retry(max_attempts=3, delay=0.5):
    """
    Decorador para reintentar operaciones de BD si fallan por problemas de conexión.
    
    Args:
        max_attempts: número máximo de intentos
        delay: tiempo de espera entre intentos (segundos)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    # Forzar cierre de conexión antes de cada intento
                    connection.close()
                    
                    return func(*args, **kwargs)
                    
                except (OperationalError, InterfaceError, DatabaseError) as e:
                    last_exception = e
                    error_msg = str(e).lower()
                    
                    logger.warning(f"DB error on attempt {attempt + 1}/{max_attempts}: {error_msg}")
                    
                    # Verificar si es un error de conexión que debemos reintentar
                    is_connection_error = any(keyword in error_msg for keyword in [
                        'connection', 'timeout', 'closed', 'terminating',
                        'pool', 'server closed', 'broken pipe', 'unexpectedly',
                        'could not connect', 'no connection', 'lost connection'
                    ])
                    
                    if is_connection_error and attempt < max_attempts - 1:
                        # Espera con backoff exponencial
                        sleep_time = delay * (2 ** attempt)  # 0.5, 1, 2 segundos
                        logger.info(f"Retrying in {sleep_time}s...")
                        time.sleep(sleep_time)
                        
                        # Forzar cierre de conexión para reconectar
                        connection.close()
                        continue
                    
                    # Si no es error de conexión o ya agotamos intentos, propagar
                    logger.error(f"DB error after {attempt + 1} attempts: {error_msg}")
                    raise
                    
            # Si agotamos intentos, lanzar última excepción
            if last_exception:
                raise last_exception
            
        return wrapper
    return decorator


def execute_query_with_retry(query, params=None, fetch_one=False, fetch_all=False):
    """
    Ejecuta una query con retry automático en caso de error de conexión.
    
    Args:
        query: SQL query
        params: parámetros de la query
        fetch_one: si True, retorna fetchone()
        fetch_all: si True, retorna fetchall()
    
    Returns:
        resultado de la query o None
    """
    @db_retry(max_attempts=3, delay=0.5)
    def _execute():
        with connection.cursor() as cur:
            cur.execute(query, params or [])
            if fetch_one:
                return cur.fetchone()
            elif fetch_all:
                return cur.fetchall()
            return None
    
    return _execute()
