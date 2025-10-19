# Cambios Críticos para Solucionar Error 500 en Render

## Fecha: 19 de Octubre 2025

### Problema Identificado
Error intermitente 500 en Render con el mensaje:
```
psycopg.OperationalError: connection failed: connection to server at "18.228.163.245", 
port 6543 failed: server closed the connection unexpectedly
```

### Root Cause
1. **Transaction Pooler de Supabase (free tier)** cierra conexiones inactivas agresivamente
2. **Django** intentaba reusar conexiones cerradas
3. **Retry logic** no estaba capturando todos los tipos de errores de BD
4. **Preload app** en Gunicorn causaba conexiones compartidas entre workers

### Soluciones Implementadas

#### 1. **settings.py** - Configuración de BD Mejorada
- ✅ `DISABLE_SERVER_SIDE_CURSORS = True` - **CRÍTICO** para pgBouncer/Pooler
- ✅ Timeouts más agresivos (5s conexión, 25s queries)
- ✅ Keepalives más frecuentes (cada 2s en lugar de 10s)
- ✅ Logging configurado para ver errores

#### 2. **db_utils.py** - Retry Logic Mejorado
- ✅ Captura `OperationalError`, `InterfaceError`, y `DatabaseError`
- ✅ `connection.close()` ANTES de cada intento
- ✅ Backoff exponencial mejorado (0.5s, 1s, 2s)
- ✅ Logging detallado de intentos

#### 3. **views.py** - LoginView Refactorizado
- ✅ Retry manual en lugar de decorador (más control)
- ✅ `connection.close()` forzado antes de cada query
- ✅ Manejo de errores más robusto
- ✅ Logging de cada intento

#### 4. **gunicorn.conf.py** - Configuración Corregida
- ✅ `preload_app = False` - **CRÍTICO** cada worker maneja su propia conexión
- ✅ `post_fork` hook - cierra conexiones heredadas
- ✅ Workers reciclados cada 500 requests (en lugar de 1000)
- ✅ Timeout aumentado a 180s

### Configuración DISABLE_SERVER_SIDE_CURSORS

**Por qué es crítico:**
- Supabase usa **pgBouncer** en modo **Transaction Pooling**
- Los cursors del lado del servidor NO son compatibles con transaction pooling
- Django por defecto usa server-side cursors para queries grandes
- Esto causa el error "server closed the connection unexpectedly"

**Referencia:**
- https://docs.djangoproject.com/en/stable/ref/databases/#transaction-pooling-server-side-cursors
- https://supabase.com/docs/guides/database/connecting-to-postgres#connection-pooler

### Testing
Ejecutar antes de deployar:
```bash
python test_connection.py
```

Todos los tests deben pasar (5/5).

### Deploy en Render
1. Commit y push de cambios
2. Verificar que start command use: `gunicorn core.wsgi -c gunicorn.conf.py`
3. Health check en: `/auth/health/`
4. Monitorear logs por 30 minutos

### Resultados Esperados
- ✅ Sin errores 500 por conexiones cerradas
- ✅ Reintentos automáticos exitosos (visibles en logs)
- ✅ Servicio estable bajo carga
- ✅ Respuestas consistentes después de inactividad

---
**Nota:** Si el problema persiste, considerar migrar a Direct Connection en lugar de Transaction Pooler, o actualizar a plan pago de Supabase.
