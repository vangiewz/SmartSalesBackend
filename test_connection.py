#!/usr/bin/env python3
"""
Script para probar la conexión a Supabase localmente antes de deployar.
Verifica que el Transaction Pooler funcione correctamente.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.db import connection, OperationalError
from smartsales.db_utils import execute_query_with_retry
import time


def test_connection():
    """Prueba la conexión básica a la BD"""
    print("🔍 Probando conexión a base de datos...")
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            if result and result[0] == 1:
                print("✅ Conexión exitosa")
                return True
            else:
                print("❌ Respuesta inesperada")
                return False
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return False


def test_retry_logic():
    """Prueba el retry logic"""
    print("\n🔍 Probando retry logic...")
    try:
        result = execute_query_with_retry(
            "SELECT 1 as test",
            fetch_one=True
        )
        if result and result[0] == 1:
            print("✅ Retry logic funciona correctamente")
            return True
        else:
            print("❌ Retry logic no devolvió resultado esperado")
            return False
    except Exception as e:
        print(f"❌ Error en retry logic: {e}")
        return False


def test_multiple_queries():
    """Prueba múltiples queries consecutivas"""
    print("\n🔍 Probando múltiples queries consecutivas...")
    try:
        for i in range(5):
            result = execute_query_with_retry(
                f"SELECT {i+1} as num",
                fetch_one=True
            )
            if not result or result[0] != i+1:
                print(f"❌ Query {i+1} falló")
                return False
            print(f"  ✓ Query {i+1} OK")
            time.sleep(0.5)
        print("✅ Todas las queries consecutivas exitosas")
        return True
    except Exception as e:
        print(f"❌ Error en queries consecutivas: {e}")
        return False


def test_connection_info():
    """Muestra información de la conexión"""
    print("\n📊 Información de conexión:")
    try:
        db_settings = connection.settings_dict
        print(f"  Host: {db_settings.get('HOST', 'N/A')}")
        print(f"  Port: {db_settings.get('PORT', 'N/A')}")
        print(f"  Name: {db_settings.get('NAME', 'N/A')}")
        print(f"  User: {db_settings.get('USER', 'N/A')}")
        print(f"  Conn Max Age: {db_settings.get('CONN_MAX_AGE', 'N/A')}")
        print(f"  Conn Health Checks: {db_settings.get('CONN_HEALTH_CHECKS', 'N/A')}")
        
        # Verificar que sea el pooler
        host = db_settings.get('HOST', '')
        port = db_settings.get('PORT', '')
        
        if 'pooler' in host and port == 6543:
            print("\n✅ Usando Transaction Pooler correctamente (puerto 6543)")
        elif port == 5432:
            print("\n⚠️  ADVERTENCIA: Usando conexión directa (puerto 5432)")
            print("   Se recomienda usar Transaction Pooler (puerto 6543) en producción")
        else:
            print(f"\n⚠️  Puerto inusual: {port}")
        
        return True
    except Exception as e:
        print(f"❌ Error obteniendo información: {e}")
        return False


def test_table_access():
    """Prueba acceso a tablas del proyecto"""
    print("\n🔍 Probando acceso a tablas...")
    try:
        # Verificar que exista la tabla usuario
        result = execute_query_with_retry(
            """
            SELECT COUNT(*) FROM usuario
            """,
            fetch_one=True
        )
        count = result[0] if result else 0
        print(f"  ✓ Tabla 'usuario': {count} registros")
        
        # Verificar que exista la tabla roles
        result = execute_query_with_retry(
            """
            SELECT COUNT(*) FROM roles
            """,
            fetch_one=True
        )
        count = result[0] if result else 0
        print(f"  ✓ Tabla 'roles': {count} registros")
        
        print("✅ Acceso a tablas exitoso")
        return True
    except Exception as e:
        print(f"❌ Error accediendo a tablas: {e}")
        print("   Asegúrate de haber ejecutado las migraciones")
        return False


def main():
    """Ejecuta todos los tests"""
    print("=" * 60)
    print("🧪 TEST DE CONEXIÓN A SUPABASE")
    print("=" * 60)
    
    tests = [
        ("Información de conexión", test_connection_info),
        ("Conexión básica", test_connection),
        ("Retry logic", test_retry_logic),
        ("Queries consecutivas", test_multiple_queries),
        ("Acceso a tablas", test_table_access),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ Error crítico en '{name}': {e}")
            results.append((name, False))
    
    # Resumen
    print("\n" + "=" * 60)
    print("📋 RESUMEN DE TESTS")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} - {name}")
    
    print(f"\nResultado: {passed}/{total} tests pasados")
    
    if passed == total:
        print("\n🎉 ¡Todos los tests pasaron! Tu configuración está lista para deploy.")
        return 0
    else:
        print("\n⚠️  Algunos tests fallaron. Revisa la configuración antes de deployar.")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⏹️  Tests interrumpidos por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error crítico: {e}")
        sys.exit(1)
