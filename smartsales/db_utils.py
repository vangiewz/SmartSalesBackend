"""
Utilidades para manejar conexiones de BD con retry logic.
Útil para Supabase Transaction Pooler en free tier.
"""
from django.db import connection, OperationalError
from functools import wraps
import time


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
                    # Cerrar conexión inactiva antes de intentar
                    if connection.connection and connection.is_usable():
                        pass  # conexión OK
                    else:
                        connection.close()  # forzar reconexión
                    
                    return func(*args, **kwargs)
                    
                except OperationalError as e:
                    last_exception = e
                    error_msg = str(e).lower()
                    
                    # Solo reintentar si es problema de conexión
                    if any(keyword in error_msg for keyword in [
                        'connection', 'timeout', 'closed', 'terminating',
                        'pool', 'server closed', 'broken pipe'
                    ]):
                        if attempt < max_attempts - 1:
                            time.sleep(delay * (attempt + 1))  # backoff exponencial
                            connection.close()  # forzar nueva conexión
                            continue
                    
                    # Si no es error de conexión, propagar inmediatamente
                    raise
                    
            # Si agotamos intentos, lanzar última excepción
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
