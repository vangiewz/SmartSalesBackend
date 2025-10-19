# SmartSales Backend - Guía de Deployment en Render

## 🚀 Deployment en Render

### 1. Configuración Inicial

#### Variables de Entorno en Render
Ve a tu servicio en Render > Environment y agrega:

```bash
SECRET_KEY=tu_secret_key_aqui
DEBUG=False
ALLOWED_HOSTS=tu-app.onrender.com

# Supabase
SUPABASE_URL=https://qauulhdqxycaeasuyoxu.supabase.co
SUPABASE_ANON_KEY=tu_anon_key
SUPABASE_SERVICE_ROLE_KEY=tu_service_role_key
SUPABASE_JWT_SECRET=tu_jwt_secret

# Database (Transaction Pooler)
DATABASE_URL=postgresql://postgres.qauulhdqxycaeasuyoxu:JBrUti0l5WSf4XZo@aws-1-sa-east-1.pooler.supabase.com:6543/postgres
```

### 2. Comandos de Build y Start

#### Build Command:
```bash
pip install --upgrade pip && pip install -r requirements.txt && python manage.py migrate --noinput && python manage.py collectstatic --noinput
```

#### Start Command (Mejorado):
```bash
gunicorn core.wsgi -c gunicorn.conf.py
```

O si prefieres manual:
```bash
gunicorn core.wsgi --workers 2 --threads 4 --timeout 120 --keep-alive 5 --log-level info
```

### 3. Configuración del Servicio

- **Region**: Oregon (US West) - para coincidir con Supabase
- **Plan**: Free
- **Health Check Path**: `/auth/health/`

### 4. Solución a Problemas de Conexión

#### Problema: Error 500 después de inactividad
**Causa**: El Transaction Pooler de Supabase cierra conexiones inactivas en el free tier.

**Solución implementada**:
1. ✅ `conn_max_age=0` - No reusar conexiones (el pooler ya lo maneja)
2. ✅ `conn_health_checks=True` - Validar conexión antes de usarla
3. ✅ Timeouts configurados en la BD
4. ✅ Retry logic automático en todas las queries
5. ✅ Health check endpoint para mantener servicio activo

#### Problema: Servicio se duerme (free tier)
**Causa**: Render duerme servicios free después de 15 min sin actividad.

**Soluciones**:

**Opción A**: Usar un servicio de ping externo
- [UptimeRobot](https://uptimerobot.com/) - Gratis, ping cada 5 min
- [Cron-Job.org](https://cron-job.org/) - Gratis, configurable
- Configurar para hacer ping a: `https://tu-app.onrender.com/auth/health/`

**Opción B**: Usar el script `keep_alive.py` (local)
```bash
python keep_alive.py https://tu-app.onrender.com/auth/health/
```

### 5. Monitoreo y Logs

Ver logs en tiempo real:
```bash
# En Render Dashboard > Logs
```

Probar health check:
```bash
curl https://tu-app.onrender.com/auth/health/
```

Respuesta esperada:
```json
{
  "status": "healthy",
  "database": "ok",
  "service": "SmartSales Backend"
}
```

## 🔧 Optimizaciones Implementadas

### Settings.py
- ✅ Connection pooling optimizado para Supabase
- ✅ Timeouts y keepalives configurados
- ✅ Health checks en cada conexión

### DB Utils (db_utils.py)
- ✅ Decorador `@db_retry` para reintentar conexiones fallidas
- ✅ Backoff exponencial en reintentos
- ✅ Detección inteligente de errores de conexión

### Views
- ✅ Todas las queries con retry automático
- ✅ Manejo de errores mejorado
- ✅ Health check endpoint

### Gunicorn (gunicorn.conf.py)
- ✅ Workers optimizados para free tier
- ✅ Reciclaje de workers cada 1000 requests
- ✅ Cierre automático de conexiones BD al reciclar workers

## 📊 Métricas Esperadas

Con estas optimizaciones deberías tener:
- ⚡ Tiempo de respuesta: < 500ms (warm)
- 🔄 Reintentos exitosos: 95%+
- 💚 Uptime: > 99% (con ping externo)
- ❌ Errores 500: < 1%

## 🐛 Troubleshooting

### Error: "server closed the connection unexpectedly"
- ✅ Resuelto con `conn_max_age=0` y retry logic

### Error: "connection timed out"
- ✅ Resuelto con timeouts configurados y keepalives

### Error: "too many connections"
- ✅ Resuelto con reciclaje de workers y cierre de conexiones

### Servicio lento después de inactividad
- Configure un ping externo cada 5-10 minutos

## 📝 Checklist de Deployment

- [ ] Variables de entorno configuradas en Render
- [ ] Build command actualizado
- [ ] Start command usando `gunicorn.conf.py`
- [ ] Health check path configurado: `/auth/health/`
- [ ] Región Oregon seleccionada
- [ ] Ping externo configurado (UptimeRobot o similar)
- [ ] Probar endpoints después del deploy
- [ ] Monitorear logs por 24h

## 🆘 Soporte

Si sigues teniendo problemas:
1. Revisa los logs en Render Dashboard
2. Verifica que el health check responda correctamente
3. Confirma que las variables de entorno estén correctas
4. Verifica que la región coincida con Supabase (Oregon/US West)

---

**Última actualización**: Octubre 2025
