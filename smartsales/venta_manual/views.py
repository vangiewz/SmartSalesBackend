import os
import json
from decimal import Decimal
from datetime import datetime

from django.db import connection, transaction
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from smartsales.rolesusuario.permissions import IsVendedorRole
from .serializers import (
    BuscarClienteSerializer,
    ClienteEncontradoSerializer,
    RegistrarVentaManualSerializer,
    ResumenVentaManualSerializer,
    BuscarProductoSerializer,
    ProductoDisponibleSerializer,
    AgregarAlCarritoSerializer,
    ItemCarritoSerializer,
    CarritoResponseSerializer,
    ActualizarCantidadSerializer,
)


class BuscarClienteView(APIView):
    """
    Vista para buscar un cliente por su correo electrónico.
    Solo accesible por vendedores.
    
    GET /api/venta-manual/buscar-cliente/?correo=cliente@ejemplo.com
    """
    permission_classes = [IsAuthenticated, IsVendedorRole]
    
    def get(self, request):
        serializer = BuscarClienteSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        
        correo = serializer.validated_data['correo'].lower().strip()
        
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, nombre, correo, telefono
                FROM usuario
                WHERE LOWER(correo) = %s
                """,
                [correo]
            )
            row = cursor.fetchone()
        
        if not row:
            return Response(
                {"detail": f"No se encontró ningún cliente con el correo '{correo}'."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        cliente_data = {
            'usuario_id': row[0],
            'nombre': row[1],
            'correo': row[2],
            'telefono': row[3] or ''
        }
        
        return Response(
            ClienteEncontradoSerializer(cliente_data).data,
            status=status.HTTP_200_OK
        )


class BuscarProductoView(APIView):
    """
    Vista para buscar productos disponibles por nombre.
    Solo accesible por vendedores.
    
    GET /api/venta-manual/buscar-producto/?busqueda=refrigerador
    """
    permission_classes = [IsAuthenticated, IsVendedorRole]
    
    def get(self, request):
        serializer = BuscarProductoSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        
        busqueda = serializer.validated_data.get('busqueda', '').strip()
        
        with connection.cursor() as cursor:
            # Si busqueda está vacía, traer todos los productos disponibles
            # Si tiene valor, buscar productos que coincidan
            if busqueda:
                query = """
                    SELECT 
                        p.id,
                        p.nombre,
                        p.precio,
                        p.stock,
                        m.nombre as marca,
                        tp.nombre as tipo,
                        p.tiempogarantia
                    FROM producto p
                    JOIN marca m ON p.marca_id = m.id
                    JOIN tipoproducto tp ON p.tipoproducto_id = tp.id
                    WHERE p.stock > 0
                    AND LOWER(p.nombre) LIKE LOWER(%s)
                    ORDER BY p.nombre
                    LIMIT 50
                """
                cursor.execute(query, [f'%{busqueda}%'])
            else:
                query = """
                    SELECT 
                        p.id,
                        p.nombre,
                        p.precio,
                        p.stock,
                        m.nombre as marca,
                        tp.nombre as tipo,
                        p.tiempogarantia
                    FROM producto p
                    JOIN marca m ON p.marca_id = m.id
                    JOIN tipoproducto tp ON p.tipoproducto_id = tp.id
                    WHERE p.stock > 0
                    ORDER BY p.nombre
                    LIMIT 50
                """
                cursor.execute(query)
            
            rows = cursor.fetchall()
        
        if not rows:
            mensaje = f"No se encontraron productos disponibles que coincidan con '{busqueda}'." if busqueda else "No tienes productos disponibles en stock."
            return Response(
                {"detail": mensaje},
                status=status.HTTP_404_NOT_FOUND
            )
        
        productos = []
        for row in rows:
            productos.append({
                'producto_id': row[0],
                'nombre': row[1],
                'precio': row[2],
                'stock': row[3],
                'marca': row[4],
                'tipo': row[5],
                'tiempo_garantia': row[6]
            })
        
        return Response(
            ProductoDisponibleSerializer(productos, many=True).data,
            status=status.HTTP_200_OK
        )


class RegistrarVentaManualView(APIView):
    """
    Vista para registrar una venta manual en mostrador.
    El vendedor selecciona el cliente por correo y los productos manualmente.
    
    Flujo:
    1. Valida cliente y productos
    2. Verifica stock disponible
    3. Crea venta, detalleventa y pago
    4. Actualiza stock
    5. Envía notificaciones (igual que webhook)
    
    POST /api/venta-manual/registrar/
    """
    permission_classes = [IsAuthenticated, IsVendedorRole]
    
    def post(self, request):
        serializer = RegistrarVentaManualSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        vendedor_id = request.user.id
        vendedor_nombre = request.user.nombre if hasattr(request.user, 'nombre') else 'Vendedor'
        
        cliente_correo = serializer.validated_data['cliente_correo'].lower().strip()
        productos = serializer.validated_data['productos']
        direccion = serializer.validated_data['direccion'].strip()
        metodo_pago = serializer.validated_data['metodo_pago']
        
        try:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    # 1. Verificar que el cliente existe
                    cursor.execute(
                        "SELECT id, nombre, correo FROM usuario WHERE LOWER(correo) = %s",
                        [cliente_correo]
                    )
                    cliente_row = cursor.fetchone()
                    
                    if not cliente_row:
                        return Response(
                            {"detail": f"No se encontró el cliente con correo '{cliente_correo}'."},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    
                    cliente_id = cliente_row[0]
                    cliente_nombre = cliente_row[1]
                    
                    # 2. Validar productos, stock y calcular total
                    total_venta = Decimal('0.00')
                    productos_validados = []
                    productos_con_stock_bajo = []
                    
                    for prod in productos:
                        producto_id = prod['producto_id']
                        cantidad = prod['cantidad']
                        
                        # Obtener información del producto
                        cursor.execute(
                            """
                            SELECT p.nombre, p.precio, p.stock, p.tiempogarantia,
                                   m.nombre as marca, tp.nombre as tipo
                            FROM producto p
                            JOIN marca m ON p.marca_id = m.id
                            JOIN tipoproducto tp ON p.tipoproducto_id = tp.id
                            WHERE p.id = %s
                            """,
                            [producto_id]
                        )
                        prod_row = cursor.fetchone()
                        
                        if not prod_row:
                            return Response(
                                {"detail": f"Producto con ID {producto_id} no encontrado."},
                                status=status.HTTP_400_BAD_REQUEST
                            )
                        
                        nombre, precio, stock, tiempo_garantia = prod_row[0], prod_row[1], prod_row[2], prod_row[3]
                        
                        # Verificar stock suficiente
                        if cantidad > stock:
                            return Response(
                                {
                                    "detail": f"Stock insuficiente para '{nombre}'. "
                                             f"Disponible: {stock}, Solicitado: {cantidad}"
                                },
                                status=status.HTTP_400_BAD_REQUEST
                            )
                        
                        subtotal = precio * cantidad
                        total_venta += subtotal
                        
                        productos_validados.append({
                            'producto_id': producto_id,
                            'nombre': nombre,
                            'precio': precio,
                            'cantidad': cantidad,
                            'subtotal': subtotal,
                            'tiempo_garantia': tiempo_garantia,
                            'stock_actual': stock
                        })
                    
                    # 3. Crear venta
                    cursor.execute(
                        """
                        INSERT INTO venta (usuario_id, total, direccion, hora)
                        VALUES (%s, %s, %s, NOW())
                        RETURNING id, hora
                        """,
                        [cliente_id, total_venta, direccion]
                    )
                    venta_row = cursor.fetchone()
                    venta_id = venta_row[0]
                    venta_hora = venta_row[1]
                    
                    # 4. Crear detalleventa y actualizar stock
                    for prod in productos_validados:
                        producto_id = prod['producto_id']
                        cantidad = prod['cantidad']
                        tiempo_garantia = prod['tiempo_garantia']
                        stock_actual = prod['stock_actual']
                        
                        # Insertar detalle de venta (trigger calcula limitegarantia automáticamente)
                        cursor.execute(
                            """
                            INSERT INTO detalleventa (venta_id, producto_id, cantidad, limitegarantia)
                            VALUES (%s, %s, %s, %s + INTERVAL '%s days')
                            """,
                            [venta_id, producto_id, cantidad, venta_hora, tiempo_garantia]
                        )
                        
                        # Actualizar stock
                        cursor.execute(
                            "UPDATE producto SET stock = stock - %s WHERE id = %s",
                            [cantidad, producto_id]
                        )
                        
                        # Verificar si el stock queda bajo (7 o menos)
                        nuevo_stock = stock_actual - cantidad
                        if nuevo_stock <= 7:
                            productos_con_stock_bajo.append({
                                'producto_id': producto_id,
                                'vendedor_id': vendedor_id,
                                'stock_nuevo': nuevo_stock
                            })
                    
                    # 5. Crear registro de pago (sin payment_intent_id, es pago manual)
                    cursor.execute(
                        """
                        INSERT INTO pagos (venta_id, total, hora)
                        VALUES (%s, %s, NOW())
                        RETURNING id
                        """,
                        [venta_id, total_venta]
                    )
                    pago_id = cursor.fetchone()[0]
                    
                    # 6. Preparar respuesta
                    respuesta = {
                        'venta_id': venta_id,
                        'cliente_nombre': cliente_nombre,
                        'cliente_correo': cliente_correo,
                        'total': float(total_venta),
                        'direccion': direccion,
                        'metodo_pago': metodo_pago,
                        'fecha': venta_hora,
                        'productos': [
                            {
                                'producto_id': p['producto_id'],
                                'nombre': p['nombre'],
                                'precio': float(p['precio']),
                                'cantidad': p['cantidad'],
                                'subtotal': float(p['subtotal'])
                            }
                            for p in productos_validados
                        ],
                        'vendedor_nombre': vendedor_nombre,
                        'pago_id': pago_id
                    }
                    
                    # 7. Enviar notificaciones después del commit
                    transaction.on_commit(lambda: self._enviar_notificaciones_venta_manual(
                        venta_id, cliente_id, productos_con_stock_bajo, vendedor_id
                    ))
                    
                    return Response(
                        ResumenVentaManualSerializer(respuesta).data,
                        status=status.HTTP_201_CREATED
                    )
        
        except Exception as e:
            return Response(
                {"detail": f"Error al registrar la venta: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _enviar_notificaciones_venta_manual(self, venta_id, cliente_id, productos_con_stock_bajo, vendedor_id):
        """
        Envía notificaciones después de registrar una venta manual.
        Usa el mismo sistema de notificaciones que el webhook.
        """
        try:
            from smartsales.notificaciones.services import NotificacionManager
            from smartsales.models import Venta, Producto
            
            # Notificar compra exitosa al cliente
            try:
                venta = Venta.objects.get(id=venta_id)
                NotificacionManager.notificar_compra_exitosa(venta)
                print(f"[VENTA_MANUAL] Notificación de compra enviada al cliente (venta {venta_id})")
            except Venta.DoesNotExist:
                print(f"[VENTA_MANUAL] No se pudo encontrar venta {venta_id}")
            except Exception as e:
                print(f"[VENTA_MANUAL] Error al notificar compra: {e}")
            
            # Notificar stock bajo al vendedor
            if productos_con_stock_bajo:
                for item in productos_con_stock_bajo:
                    try:
                        producto = Producto.objects.get(id=item['producto_id'])
                        NotificacionManager.notificar_stock_bajo(producto)
                        print(f"[VENTA_MANUAL] Notificación de stock bajo enviada para producto {item['producto_id']}")
                    except Producto.DoesNotExist:
                        print(f"[VENTA_MANUAL] No se pudo encontrar producto {item['producto_id']}")
                    except Exception as e:
                        print(f"[VENTA_MANUAL] Error al notificar stock bajo: {e}")
            
        except Exception as e:
            print(f"[VENTA_MANUAL] Error general al enviar notificaciones: {e}")


# ===============================================================
# NUEVAS VISTAS: CARRITO DE VENTA MANUAL
# ===============================================================

# Almacenamiento temporal del carrito en memoria (por sesión de vendedor)
# En producción, considerar usar Redis o base de datos
carritos_vendedores = {}


class AgregarAlCarritoView(APIView):
    """
    Vista para agregar un producto al carrito de venta manual.
    Valida stock disponible antes de agregar.
    
    POST /api/venta-manual/carrito/agregar/
    """
    permission_classes = [IsAuthenticated, IsVendedorRole]
    
    def post(self, request):
        serializer = AgregarAlCarritoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        vendedor_id = str(request.user.id)
        producto_id = serializer.validated_data['producto_id']
        cantidad = serializer.validated_data['cantidad']
        
        # Obtener información del producto
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT p.id, p.nombre, p.precio, p.stock,
                       m.nombre as marca, tp.nombre as tipo
                FROM producto p
                JOIN marca m ON p.marca_id = m.id
                JOIN tipoproducto tp ON p.tipoproducto_id = tp.id
                WHERE p.id = %s
                """,
                [producto_id]
            )
            row = cursor.fetchone()
        
        if not row:
            return Response(
                {"detail": f"Producto con ID {producto_id} no encontrado."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        prod_id, nombre, precio, stock, marca, tipo = row
        
        # Inicializar carrito si no existe
        if vendedor_id not in carritos_vendedores:
            carritos_vendedores[vendedor_id] = {}
        
        carrito = carritos_vendedores[vendedor_id]
        
        # Calcular cantidad total en carrito (existente + nueva)
        cantidad_en_carrito = carrito.get(producto_id, {}).get('cantidad', 0)
        cantidad_total = cantidad_en_carrito + cantidad
        
        # Validar stock disponible
        if cantidad_total > stock:
            return Response(
                {
                    "detail": f"Stock insuficiente para '{nombre}'. "
                             f"Disponible: {stock}, En carrito: {cantidad_en_carrito}, Solicitado: {cantidad}"
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Agregar o actualizar producto en carrito
        if producto_id in carrito:
            carrito[producto_id]['cantidad'] = cantidad_total
            carrito[producto_id]['subtotal'] = float(precio) * cantidad_total
        else:
            carrito[producto_id] = {
                'producto_id': producto_id,
                'nombre': nombre,
                'precio': float(precio),
                'cantidad': cantidad_total,
                'subtotal': float(precio) * cantidad_total,
                'stock_disponible': stock,
                'marca': marca,
                'tipo': tipo
            }
        
        # Preparar respuesta con el carrito actualizado
        items = list(carrito.values())
        total = sum(item['subtotal'] for item in items)
        
        response_data = {
            'items': items,
            'total': total,
            'cantidad_items': len(items)
        }
        
        return Response(
            CarritoResponseSerializer(response_data).data,
            status=status.HTTP_200_OK
        )


class ObtenerCarritoView(APIView):
    """
    Vista para obtener el carrito actual del vendedor.
    
    GET /api/venta-manual/carrito/
    """
    permission_classes = [IsAuthenticated, IsVendedorRole]
    
    def get(self, request):
        vendedor_id = str(request.user.id)
        carrito = carritos_vendedores.get(vendedor_id, {})
        
        items = list(carrito.values())
        total = sum(item['subtotal'] for item in items)
        
        response_data = {
            'items': items,
            'total': total,
            'cantidad_items': len(items)
        }
        
        return Response(
            CarritoResponseSerializer(response_data).data,
            status=status.HTTP_200_OK
        )


class ActualizarCantidadCarritoView(APIView):
    """
    Vista para actualizar la cantidad de un producto en el carrito.
    
    PUT /api/venta-manual/carrito/actualizar/
    """
    permission_classes = [IsAuthenticated, IsVendedorRole]
    
    def put(self, request):
        serializer = ActualizarCantidadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        vendedor_id = str(request.user.id)
        producto_id = serializer.validated_data['producto_id']
        cantidad = serializer.validated_data['cantidad']
        
        carrito = carritos_vendedores.get(vendedor_id, {})
        
        if producto_id not in carrito:
            return Response(
                {"detail": f"Producto con ID {producto_id} no está en el carrito."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Verificar stock disponible
        stock_disponible = carrito[producto_id]['stock_disponible']
        if cantidad > stock_disponible:
            return Response(
                {
                    "detail": f"Stock insuficiente. Disponible: {stock_disponible}, Solicitado: {cantidad}"
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Actualizar cantidad
        carrito[producto_id]['cantidad'] = cantidad
        carrito[producto_id]['subtotal'] = carrito[producto_id]['precio'] * cantidad
        
        # Preparar respuesta
        items = list(carrito.values())
        total = sum(item['subtotal'] for item in items)
        
        response_data = {
            'items': items,
            'total': total,
            'cantidad_items': len(items)
        }
        
        return Response(
            CarritoResponseSerializer(response_data).data,
            status=status.HTTP_200_OK
        )


class EliminarDelCarritoView(APIView):
    """
    Vista para eliminar un producto del carrito.
    
    DELETE /api/venta-manual/carrito/eliminar/{producto_id}/
    """
    permission_classes = [IsAuthenticated, IsVendedorRole]
    
    def delete(self, request, producto_id):
        vendedor_id = str(request.user.id)
        carrito = carritos_vendedores.get(vendedor_id, {})
        
        if producto_id not in carrito:
            return Response(
                {"detail": f"Producto con ID {producto_id} no está en el carrito."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Eliminar producto
        del carrito[producto_id]
        
        # Preparar respuesta
        items = list(carrito.values())
        total = sum(item['subtotal'] for item in items)
        
        response_data = {
            'items': items,
            'total': total,
            'cantidad_items': len(items)
        }
        
        return Response(
            CarritoResponseSerializer(response_data).data,
            status=status.HTTP_200_OK
        )


class VaciarCarritoView(APIView):
    """
    Vista para vaciar completamente el carrito.
    
    DELETE /api/venta-manual/carrito/vaciar/
    """
    permission_classes = [IsAuthenticated, IsVendedorRole]
    
    def delete(self, request):
        vendedor_id = str(request.user.id)
        
        # Vaciar carrito
        if vendedor_id in carritos_vendedores:
            carritos_vendedores[vendedor_id] = {}
        
        response_data = {
            'items': [],
            'total': 0,
            'cantidad_items': 0
        }
        
        return Response(
            CarritoResponseSerializer(response_data).data,
            status=status.HTTP_200_OK
        )
