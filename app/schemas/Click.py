from pydantic import BaseModel


class InvoiceCreate(BaseModel):
    amount: float
    phone_number: str
    transaction_id: str


class CardTokenCreate(BaseModel):
    card_number: str
    expire_date: str
    temporary: int = 0


class CardTokenVerify(BaseModel):
    card_id: str
    sms_code: str


class PaymentWithToken(BaseModel):
    card_id: str
    amount: float
    transaction_id: str


class PaymentCard(BaseModel):
    id: str
    card_number: str
    expiry_at: str
    is_default: bool
    is_active: bool