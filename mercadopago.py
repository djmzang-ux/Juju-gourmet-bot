import httpx
from decimal import Decimal
from .base import PaymentProvider, PaymentRequest, PaymentResponse
from ..config import settings

class MercadoPagoProvider(PaymentProvider):
    async def create_pix(self, request: PaymentRequest) -> PaymentResponse:
        if not settings.mercadopago_access_token:
            raise RuntimeError("MERCADOPAGO_ACCESS_TOKEN não configurado")

        # Integração preparada para Checkout API / Pix.
        # Confirme os campos exigidos pela conta/ambiente atual do Mercado Pago
        # antes de produção. Nunca exponha o Access Token ao cliente.
        headers = {
            "Authorization": f"Bearer {settings.mercadopago_access_token}",
            "Content-Type": "application/json",
            "X-Idempotency-Key": f"juju-order-{request.order_id}",
        }
        payload = {
            "transaction_amount": float(request.amount),
            "description": request.description,
            "payment_method_id": "pix",
            "payer": {"email": f"pedido-{request.order_id}@example.invalid"},
        }

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                "https://api.mercadopago.com/v1/payments",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        poi = data.get("point_of_interaction", {})
        tx = poi.get("transaction_data", {})
        return PaymentResponse(
            provider_id=str(data["id"]),
            qr_code=tx.get("qr_code"),
            qr_code_base64=tx.get("qr_code_base64"),
            status=data.get("status", "pending"),
        )
