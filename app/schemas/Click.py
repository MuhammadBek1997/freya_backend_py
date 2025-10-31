from app.models.base import BaseModel


class InvoiceCreate(BaseModel):
    amount: float
    phone_number: str
    transaction_id: str


class CardTokenCreate(BaseModel):
    card_number: str
    expire_date: str
    temporary: int = 0


class CardTokenVerify(BaseModel):
    card_id: int
    sms_code: str


class PaymentWithToken(BaseModel):
    card_id: int
    amount: float
    transaction_id: str


class PaymentCard(BaseModel):
    id: int
    card_number: str
    expiry_at: str
    is_default: bool
    is_active: bool
    is_verified: bool