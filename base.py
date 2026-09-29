from dataclasses import dataclass
from decimal import Decimal

@dataclass
class PaymentRequest:
    order_id: int
    amount: Decimal
    description: str

@dataclass
class PaymentResponse:
    provider_id: str
    qr_code: str | None
    qr_code_base64: str | None
    status: str

class PaymentProvider:
    async def create_pix(self, request: PaymentRequest) -> PaymentResponse:
        raise NotImplementedError
