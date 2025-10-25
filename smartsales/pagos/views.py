import os
import json
import stripe
from decimal import Decimal
from django.db import connection, transaction
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
                automatic_payment_methods={
                    'enabled': True,
                }
            )
            
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
                    {"detail": "El pago no se completó exitosamente."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Extraer metadata para buscar la venta
            metadata = payment_intent.metadata
            usuario_id = metadata['usuario_id']
            direccion_texto = metadata['direccion_texto']
            carrito = json.loads(metadata['carrito_json'])
            total_pagado = Decimal(payment_intent.amount) / Decimal(100)
            
            # Buscar la venta creada por el webhook (con reintentos)
            venta_id = None
            max_intentos = 3
            
            for intento in range(max_intentos):
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT id FROM venta 
                        WHERE usuario_id = %s 
                        AND total = %s 
                        AND direccion = %s
                        AND hora >= NOW() - INTERVAL '10 minutes'
                        ORDER BY hora DESC
                        LIMIT 1
                        """,
                        [usuario_id, total_pagado, direccion_texto]
                    )
                    row = cursor.fetchone()
                    if row:
                        venta_id = row[0]
                        print(f"[CONFIRMAR-PAGO] Venta encontrada: {venta_id}")
                        break
                
                # Si no encontró la venta y quedan intentos, esperar un poco
                if not venta_id and intento < max_intentos - 1:
                    print(f"[CONFIRMAR-PAGO] Venta no encontrada, esperando... (intento {intento + 1}/{max_intentos})")
                    import time
                    time.sleep(1)  # Esperar 1 segundo
            
            # Si después de los reintentos no existe, crearla UNA SOLA VEZ
            if not venta_id:
                print(f"[CONFIRMAR-PAGO] Venta no encontrada después de {max_intentos} intentos, creando...")
                
                try:
                    with transaction.atomic():
                        with connection.cursor() as cursor:
                            # Crear venta
                            cursor.execute(
                                """
                                INSERT INTO venta (usuario_id, total, direccion)
                                VALUES (%s, %s, %s)
                                RETURNING id
                                """,
                                [usuario_id, total_pagado, direccion_texto]
                            )
                        venta_id = cursor.fetchone()[0]
                        print(f"[CONFIRMAR-PAGO] Venta creada: {venta_id}")
                        
                        # Obtener URL del recibo de Stripe ANTES de crear el pago
                        charge_id = payment_intent.latest_charge
                        receipt_url = None
                        if charge_id:
                            try:
                                charge = stripe.Charge.retrieve(charge_id)
                                receipt_url = charge.receipt_url
                                print(f"[CONFIRMAR-PAGO] Receipt URL obtenido: {receipt_url}")
                            except Exception as e:
                                print(f"[CONFIRMAR-PAGO] Error obteniendo receipt: {str(e)}")
                        
                        # Crear pago con receipt_url
                        cursor.execute(
                            """
                            INSERT INTO pagos (venta_id, total, receipt_url)
                            VALUES (%s, %s, %s)
                            """,
                            [venta_id, total_pagado, receipt_url]
                        )
                        
                        # 3. Crear detalleventa y restar stock
                        for item in carrito:
                            producto_id = item['producto_id']
                            cantidad = item['cantidad']
                            
                            # Obtener tiempogarantia
                            cursor.execute(
                                "SELECT tiempogarantia, stock FROM producto WHERE id = %s",
                                [producto_id]
                            )
                            row = cursor.fetchone()
                            if not row:
                                raise Exception(f"Producto {producto_id} no encontrado")
                            
                            tiempo_garantia, stock_actual = row
                            
                            if cantidad > stock_actual:
                                raise Exception(f"Stock insuficiente para producto {producto_id}")
                            
                            # Insertar detalle
                            cursor.execute(
                                """
                                INSERT INTO detalleventa (venta_id, producto_id, cantidad, limitegarantia)
                                VALUES (%s, %s, %s, 
                                    (SELECT hora FROM venta WHERE id = %s) + INTERVAL '1 day' * %s
                                )
                                """,
                                [venta_id, producto_id, cantidad, venta_id, tiempo_garantia]
                            )
                            
                            # Restar stock
                            cursor.execute(
                                """
                                UPDATE producto
                                SET stock = stock - %s
                                WHERE id = %s
                                """,
                                [cantidad, producto_id]
                            )
                except Exception as e:
                    print(f"[CONFIRMAR-PAGO] Error creando venta: {str(e)}")
                    return Response(
                        {"detail": "Error al procesar la compra. Por favor contacta a soporte."},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
            
            # Obtener URL del recibo de Stripe
            charge_id = payment_intent.latest_charge
            receipt_url = None
            
            if charge_id:
                try:
                    charge = stripe.Charge.retrieve(charge_id)
                    receipt_url = charge.receipt_url
                except:
                    pass
            
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
        
        # Procesar evento de pago completado
        if event['type'] == 'payment_intent.succeeded':
            payment_intent = event['data']['object']
            payment_intent_id = payment_intent['id']
            metadata = payment_intent['metadata']
            
            print(f"[WEBHOOK] Processing payment_intent.succeeded: {payment_intent_id}")
            
            # Extraer datos del metadata
            usuario_id = metadata['usuario_id']
            direccion_texto = metadata['direccion_texto']
            carrito = json.loads(metadata['carrito_json'])
            total_pagado = Decimal(payment_intent['amount']) / Decimal(100)
            
            # ===== VERIFICAR SI YA EXISTE LA VENTA =====
            # Evitar duplicados si el webhook se llama múltiples veces
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id FROM venta 
                    WHERE usuario_id = %s 
                    AND total = %s 
                    AND direccion = %s
                    AND hora >= NOW() - INTERVAL '1 minute'
                    LIMIT 1
                    """,
                    [usuario_id, total_pagado, direccion_texto]
                )
                venta_existente = cursor.fetchone()
                
                if venta_existente:
                    print(f"[WEBHOOK] Venta ya existe: {venta_existente[0]}")
                    return Response({"status": "already_processed"}, status=status.HTTP_200_OK)
            
            # ===== TRANSACCIÓN ATÓMICA =====
            try:
                with transaction.atomic():
                    with connection.cursor() as cursor:
                        # 1. Crear venta
                        cursor.execute(
                            """
                            INSERT INTO venta (usuario_id, total, direccion)
                            VALUES (%s, %s, %s)
                            RETURNING id
                            """,
                            [usuario_id, total_pagado, direccion_texto]
                        )
                        venta_id = cursor.fetchone()[0]
                        print(f"[WEBHOOK] Venta creada: {venta_id}")
                        
                        # Obtener URL del recibo de Stripe
                        charge_id = payment_intent.get('latest_charge')
                        receipt_url = None
                        if charge_id:
                            try:
                                charge = stripe.Charge.retrieve(charge_id)
                                receipt_url = charge.receipt_url
                                print(f"[WEBHOOK] Receipt URL obtenido: {receipt_url}")
                            except Exception as e:
                                print(f"[WEBHOOK] Error obteniendo receipt: {str(e)}")
                        
                        # Crear pago con receipt_url
                        cursor.execute(
                            """
                            INSERT INTO pagos (venta_id, total, receipt_url)
                            VALUES (%s, %s, %s)
                            """,
                            [venta_id, total_pagado, receipt_url]
                        )
                        
                        # 3. Crear detalleventa y restar stock
                        for item in carrito:
                            producto_id = item['producto_id']
                            cantidad = item['cantidad']
                            
                            # Re-validar stock y obtener tiempogarantia
                            cursor.execute(
                                "SELECT nombre, stock, tiempogarantia FROM producto WHERE id = %s",
                                [producto_id]
                            )
                            row = cursor.fetchone()
                            
                            if not row:
                                raise Exception(f"Producto {producto_id} no encontrado")
                            
                            nombre_producto, stock_actual, tiempo_garantia = row
                            
                            if cantidad > stock_actual:
                                raise Exception(
                                    f"Stock insuficiente para '{nombre_producto}'. "
                                    f"Disponible: {stock_actual}, Solicitado: {cantidad}"
                                )
                            
                            # Insertar detalle de venta
                            # limitegarantia = hora_venta + tiempogarantia días
                            cursor.execute(
                                """
                                INSERT INTO detalleventa (venta_id, producto_id, cantidad, limitegarantia)
                                VALUES (%s, %s, %s, 
                                    (SELECT hora FROM venta WHERE id = %s) + INTERVAL '1 day' * %s
                                )
                                """,
                                [venta_id, producto_id, cantidad, venta_id, tiempo_garantia]
                            )
                            
                            cursor.execute(
                                """
                                UPDATE producto
                                SET stock = stock - %s
                                WHERE id = %s
                                """,
                                [cantidad, producto_id]
                            )
                            
                            print(f"[WEBHOOK] Producto {producto_id}: stock actualizado (-{cantidad})")
                
                print(f"[WEBHOOK] Procesamiento exitoso para venta {venta_id}")
                return Response({"status": "success", "venta_id": venta_id}, status=status.HTTP_200_OK)
                
            except Exception as e:
                print(f"[WEBHOOK] Error procesando webhook: {str(e)}")
                return Response(
                    {"detail": "Error al procesar el pago."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        # Otros tipos de eventos (ignorar)
        return Response({"status": "ignored"}, status=status.HTTP_200_OK)
