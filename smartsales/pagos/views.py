import os
import json
import stripe
from decimal import Decimal
from django.db import connection, transaction
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status

from .serializers import IniciarCheckoutSerializer


class ObtenerPublicKeyView(APIView):
    """
    Vista pública para obtener la Stripe Public Key.
    El frontend llama a este endpoint para obtener la clave pública centralizada.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        public_key = os.getenv('STRIPE_PUBLISHABLE_KEY')
        
        if not public_key:
            return Response(
                {"detail": "Stripe no está configurado correctamente."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        return Response({
            'publicKey': public_key
        })


class IniciarCheckoutView(APIView):
    """
    Vista para iniciar el proceso de checkout con Stripe Payment Intents.
    Valida stock, precios y crea un Payment Intent para pago integrado.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Validar datos de entrada
        serializer = IniciarCheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        usuario_id = request.user.id
        validated_data = serializer.validated_data
        
        # ===== LÓGICA DE DIRECCIÓN (FLEXIBLE) =====
        id_dir = validated_data.get('id_direccion')
        txt_dir = validated_data.get('direccion_manual')
        direccion_para_venta = None
        
        if id_dir:
            # Validar que la dirección pertenezca al usuario
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT direccion FROM direcciones WHERE id = %s AND usuario_id = %s",
                    [id_dir, usuario_id]
                )
                row = cursor.fetchone()
            
            if not row:
                return Response(
                    {"detail": "Dirección no encontrada o no pertenece al usuario."},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            direccion_para_venta = row[0]
        
        elif txt_dir:
            direccion_para_venta = txt_dir.strip()
        
        # ===== VALIDACIÓN DE STOCK Y PRECIOS =====
        items = validated_data['items']
        carrito_para_metadata = []
        descripcion_items = []
        total_calculado = Decimal('0.00')
        
        with connection.cursor() as cursor:
            for item in items:
                producto_id = item['producto_id']  # ✅ Cambiado de id_producto a producto_id
                cantidad = item['cantidad']
                
                # Obtener producto
                cursor.execute(
                    "SELECT nombre, precio, stock FROM producto WHERE id = %s",
                    [producto_id]
                )
                row = cursor.fetchone()
                
                if not row:
                    return Response(
                        {"detail": f"Producto con ID {producto_id} no encontrado."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                nombre, precio, stock = row
                
                # Validar stock
                if cantidad > stock:
                    return Response(
                        {
                            "detail": f"Stock insuficiente para '{nombre}'. "
                                     f"Disponible: {stock}, Solicitado: {cantidad}"
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Guardar para metadata y descripción
                carrito_para_metadata.append({
                    'producto_id': producto_id,  # ✅ Cambiado de id_producto a producto_id
                    'cantidad': cantidad,
                    'precio': float(precio),
                    'nombre': nombre
                })
                
                descripcion_items.append(f"{nombre} x{cantidad}")
                total_calculado += precio * cantidad
        
        # ===== CREAR PAYMENT INTENT DE STRIPE =====
        stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
        
        if not stripe.api_key:
            return Response(
                {"detail": "Configuración de Stripe incompleta."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Metadata para el webhook
        metadata = {
            'usuario_id': str(usuario_id),
            'direccion_texto': direccion_para_venta,
            'carrito_json': json.dumps(carrito_para_metadata)
        }
        
        try:
            # Crear Payment Intent (monto en centavos)
            payment_intent = stripe.PaymentIntent.create(
                amount=int(total_calculado * 100),
                currency='usd',
                metadata=metadata,
                description=f"Compra: {', '.join(descripcion_items[:3])}" + 
                           (f" y {len(descripcion_items) - 3} más" if len(descripcion_items) > 3 else ""),
                payment_method_types=['card'],  # Especificar solo tarjetas (no requiere return_url)
            )
            
            # 🔥 AUTO-CONFIRMACIÓN PARA MÓVIL
            # Detectar si la petición viene desde la app móvil
            platform = request.META.get('HTTP_X_PLATFORM', '')
            auto_confirm = platform == 'mobile' or settings.DEBUG
            
            if auto_confirm:
                try:
                    # Confirmar el Payment Intent con tarjeta de prueba de Stripe
                    payment_intent = stripe.PaymentIntent.confirm(
                        payment_intent.id,
                        payment_method='pm_card_visa',  # Tarjeta de prueba: 4242 4242 4242 4242
                    )
                    print(f'✅ Payment Intent {payment_intent.id} confirmado automáticamente para móvil')
                except stripe.error.StripeError as e:
                    print(f'❌ Error al confirmar Payment Intent: {e}')
                    # No hacer fail, dejar que el cliente lo intente
            
            return Response({
                'clientSecret': payment_intent.client_secret,
                'paymentIntentId': payment_intent.id
            })
            
        except stripe.error.StripeError as e:
            return Response(
                {"detail": f"Error al crear Payment Intent: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ConfirmarPagoView(APIView):
    """
    Vista para obtener el comprobante de Stripe después del pago.
    SOLO OBTIENE EL RECEIPT_URL, NO CREA VENTAS.
    Las ventas se crean ÚNICAMENTE por el webhook.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        payment_intent_id = request.data.get('paymentIntentId')
        
        if not payment_intent_id:
            return Response(
                {"detail": "paymentIntentId es requerido."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
        
        try:
            # Obtener el Payment Intent desde Stripe
            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            
            # Verificar que el pago fue exitoso
            if payment_intent.status != 'succeeded':
                return Response(
                    {"detail": f"El pago no se completó exitosamente. Status: {payment_intent.status}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Buscar la venta creada por el webhook usando payment_intent_id
            venta_id = None
            receipt_url = None
            max_intentos = 5
            
            for intento in range(max_intentos):
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT venta_id, receipt_url 
                        FROM pagos 
                        WHERE payment_intent_id = %s
                        """,
                        [payment_intent_id]
                    )
                    row = cursor.fetchone()
                    if row:
                        venta_id = row[0]
                        receipt_url = row[1]
                        break
                
                if not venta_id and intento < max_intentos - 1:
                    import time
                    time.sleep(1)
            
            if not venta_id:
                return Response(
                    {"detail": "La venta aún no ha sido procesada. Intenta nuevamente en unos segundos."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            return Response({
                "status": "success",
                "venta_id": venta_id,
                "receipt_url": receipt_url,
                "message": "Pago verificado exitosamente."
            }, status=status.HTTP_200_OK)
                
        except stripe.error.StripeError as e:
            return Response(
                {"detail": f"Error al verificar pago con Stripe: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            return Response(
                {"detail": f"Error inesperado: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class StripeWebhookView(APIView):
    """
    Vista para procesar webhooks de Stripe.
    ⚠️ IMPORTANTE: Esta es la ÚNICA vía para crear ventas (centralizada).
    El frontend NO debe llamar a /confirmar-pago/, solo debe esperar el webhook.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
        webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')
        
        if not webhook_secret:
            print("[WEBHOOK] Webhook secret no configurado")
            return Response({"status": "ignored"}, status=status.HTTP_200_OK)
        
        # Verificar firma de Stripe
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, webhook_secret
            )
        except ValueError:
            return Response(
                {"detail": "Payload inválido."},
                status=status.HTTP_400_BAD_REQUEST
            )
        except stripe.error.SignatureVerificationError:
            return Response(
                {"detail": "Firma inválida."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Procesar SOLO el evento payment_intent.succeeded (ignorar todos los demás)
        if event['type'] != 'payment_intent.succeeded':
            return Response({"status": "ignored"}, status=status.HTTP_200_OK)
        
        payment_intent = event['data']['object']
        payment_intent_id = payment_intent['id']
        metadata = payment_intent['metadata']
        
        # Extraer datos del metadata
        usuario_id = metadata['usuario_id']
        direccion_texto = metadata['direccion_texto']
        carrito = json.loads(metadata['carrito_json'])
        total_pagado = Decimal(payment_intent['amount']) / Decimal(100)
        
        # Lock por payment_intent_id
        import hashlib
        lock_id = int(hashlib.md5(payment_intent_id.encode()).hexdigest()[:15], 16) % 2147483647
        
        try:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    # Adquirir lock
                    cursor.execute("SELECT pg_advisory_xact_lock(%s)", [lock_id])
                    
                    # Verificar si ya existe
                    cursor.execute("SELECT venta_id FROM pagos WHERE payment_intent_id = %s", [payment_intent_id])
                    existing = cursor.fetchone()
                    if existing:
                        return Response({"status": "already_processed"}, status=status.HTTP_200_OK)
                    
                    # Crear venta
                    cursor.execute(
                        "INSERT INTO venta (usuario_id, total, direccion) VALUES (%s, %s, %s) RETURNING id",
                        [usuario_id, total_pagado, direccion_texto]
                    )
                    venta_id = cursor.fetchone()[0]
                    
                    # Obtener receipt
                    receipt_url = None
                    charge_id = payment_intent.get('latest_charge')
                    if charge_id:
                        try:
                            charge = stripe.Charge.retrieve(charge_id)
                            receipt_url = charge.receipt_url
                        except:
                            pass
                    
                    # Crear pago
                    cursor.execute(
                        "INSERT INTO pagos (venta_id, total, receipt_url, payment_intent_id) VALUES (%s, %s, %s, %s)",
                        [venta_id, total_pagado, receipt_url, payment_intent_id]
                    )
                    
                    # Crear detalles y actualizar stock
                    productos_con_stock_bajo = []
                    for item in carrito:
                        producto_id = item['producto_id']
                        cantidad = item['cantidad']
                        
                        cursor.execute("SELECT stock, tiempogarantia, id_vendedor FROM producto WHERE id = %s", [producto_id])
                        row = cursor.fetchone()
                        if not row or row[0] < cantidad:
                            raise Exception(f"Stock insuficiente")
                        
                        stock_actual = row[0]
                        id_vendedor = row[2]
                        
                        cursor.execute(
                            "INSERT INTO detalleventa (venta_id, producto_id, cantidad, limitegarantia) VALUES (%s, %s, %s, (SELECT hora FROM venta WHERE id = %s) + INTERVAL '1 day' * %s)",
                            [venta_id, producto_id, cantidad, venta_id, row[1]]
                        )
                        
                        cursor.execute("UPDATE producto SET stock = stock - %s WHERE id = %s", [cantidad, producto_id])
                        
                        # Verificar si el stock queda en 7 o menos
                        nuevo_stock = stock_actual - cantidad
                        if nuevo_stock <= 7:
                            productos_con_stock_bajo.append({
                                'producto_id': producto_id,
                                'vendedor_id': id_vendedor,
                                'stock_nuevo': nuevo_stock
                            })
                    
                    print(f"[WEBHOOK] Venta {venta_id} creada para PI {payment_intent_id}")
                    
                    # Crear notificaciones fuera de la transacción principal
                    from django.db import connection as notif_conn
                    if notif_conn.connection is not None:
                        # Usar una nueva conexión para notificaciones (no bloquear la transacción)
                        pass
                    
                    # Devolver respuesta primero
                    response_data = {"status": "success", "venta_id": venta_id}
                    
                    # Programar notificaciones después del commit
                    transaction.on_commit(lambda: _enviar_notificaciones_post_venta(
                        venta_id, usuario_id, total_pagado, productos_con_stock_bajo
                    ))
                    
                    return Response(response_data, status=status.HTTP_200_OK)
                    
        except Exception as e:
            if 'unique constraint' in str(e).lower() or 'duplicate key' in str(e).lower():
                return Response({"status": "already_processed"}, status=status.HTTP_200_OK)
            print(f"[WEBHOOK] Error: {str(e)}")
            return Response({"detail": "Error procesando pago"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def _enviar_notificaciones_post_venta(venta_id, usuario_id, total_pagado, productos_con_stock_bajo):
    """
    Función helper para enviar notificaciones después de crear una venta
    Se ejecuta después del commit de la transacción
    """
    try:
        from smartsales.notificaciones.services import NotificacionManager
        from smartsales.models import Venta
        
        # Obtener la venta completa
        try:
            venta = Venta.objects.get(id=venta_id)
        except Venta.DoesNotExist:
            print(f"[NOTIF] No se pudo encontrar venta {venta_id}")
            return
        
        # 1. Notificar compra exitosa al comprador
        NotificacionManager.notificar_compra_exitosa(venta)
        print(f"[NOTIF] Notificación de compra enviada para venta {venta_id}")
        
        # 2. Notificar stock bajo a vendedores
        if productos_con_stock_bajo:
            from smartsales.models import Producto
            for item in productos_con_stock_bajo:
                try:
                    producto = Producto.objects.get(id=item['producto_id'])
                    NotificacionManager.notificar_stock_bajo(producto)
                    print(f"[NOTIF] Notificación de stock bajo enviada para producto {item['producto_id']}")
                except Producto.DoesNotExist:
                    print(f"[NOTIF] No se pudo encontrar producto {item['producto_id']}")
                    continue
    
    except Exception as e:
        print(f"[NOTIF] Error al enviar notificaciones: {e}")
        # No re-lanzar la excepción para no afectar el flujo principal
