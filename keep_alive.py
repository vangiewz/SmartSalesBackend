#!/usr/bin/env python3
"""
Script para hacer ping al health check y mantener el servicio activo.
Útil para el free tier de Render que se duerme después de 15 min de inactividad.

Uso:
    python keep_alive.py https://tu-app.onrender.com/auth/health/

Puedes configurar un servicio externo como UptimeRobot o Cron-Job.org
para ejecutar este endpoint cada 5-10 minutos.
"""

import sys
import requests
import time
from datetime import datetime


def ping_health_check(url, interval=300):
    """
    Hace ping al health check cada X segundos.
    
    Args:
        url: URL del health check endpoint
        interval: intervalo en segundos (default: 5 min)
    """
    print(f"🔄 Iniciando keep-alive para: {url}")
    print(f"⏰ Intervalo: {interval} segundos\n")
    
    while True:
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                status = data.get('status', 'unknown')
                db_status = data.get('database', 'unknown')
                print(f"✅ [{timestamp}] Status: {status} | DB: {db_status}")
            else:
                print(f"⚠️  [{timestamp}] HTTP {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ [{timestamp}] Error: {str(e)}")
        
        time.sleep(interval)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❌ Error: Debes proporcionar la URL del health check")
        print("\nUso:")
        print("  python keep_alive.py https://tu-app.onrender.com/auth/health/")
        print("\nPara cambiar el intervalo (en segundos):")
        print("  python keep_alive.py https://tu-app.onrender.com/auth/health/ 600")
        sys.exit(1)
    
    url = sys.argv[1]
    interval = int(sys.argv[2]) if len(sys.argv) > 2 else 300
    
    try:
        ping_health_check(url, interval)
    except KeyboardInterrupt:
        print("\n\n⏹️  Keep-alive detenido por el usuario")
        sys.exit(0)
