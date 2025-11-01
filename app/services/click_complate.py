from datetime import datetime
from dateutil.relativedelta import relativedelta
import logging
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import SessionLocal
from app.models.payment import ClickPayment
from app.models.user import User
from app.models.employee import EmployeePostLimit
from app.models.user_premium import UserPremium


class Payment(BaseModel):
    id: str
    created_at: datetime
    updated_at: datetime
    paymet_id: int
    payment_for: str
    amount: str
    status: str

    class Config:
        from_attributes = True


def complate_payment(payment: ClickPayment, db: Session = None):
    """Payment completion business logic.

    Supports two patterns in payment.payment_for:
    - "post_{employee_id}_{count}" → increment EmployeePostLimit.total_paid_posts
    - "premium_{user_id}_{months}" → extend/create UserPremium by given months
    """
    logger = logging.getLogger("ClickComplete")
    try:
        # Telegram debug helper removed; using pure business logic

        if db is None:
            db = SessionLocal()

        # Parse payment_for: e.g., "premium_{user_id}_{months}" or "post_{employee_id}_{count}"
        try:
            tokens = (payment.payment_for or "").split("_")
        except Exception:
            tokens = []

        if len(tokens) < 3:
            logger.error(f"Invalid payment_for format: {payment.payment_for}")
            return

        action, entity_id, qty_str = tokens[0], tokens[1], tokens[2]
        try:
            quantity = int(qty_str)
        except Exception:
            logger.error(f"Invalid quantity in payment_for: {payment.payment_for}")
            return

        if action == "post":
            # Grant paid post slots to employee
            limits = (
                db.query(EmployeePostLimit)
                .filter(EmployeePostLimit.employee_id == entity_id)
                .first()
            )
            if not limits:
                limits = EmployeePostLimit(employee_id=entity_id, free_posts_used=0, total_paid_posts=0)
                db.add(limits)
                db.commit()
                db.refresh(limits)

            limits.total_paid_posts = int(limits.total_paid_posts or 0) + quantity
            db.commit()
            logger.info(
                f"Employee {entity_id} granted {quantity} paid post(s). Total paid posts: {limits.total_paid_posts}"
            )

        elif action == "premium":
            # Grant premium months to user
            user = db.query(User).filter(User.id == entity_id).first()
            if not user:
                logger.error(f"User not found for premium: {entity_id}")
                return

            now = datetime.utcnow()

            # Find active premium record
            premium = (
                db.query(UserPremium)
                .filter(UserPremium.user_id == entity_id, UserPremium.is_active == True)
                .order_by(UserPremium.end_date.desc())
                .first()
            )

            # Extend by calendar months using relativedelta
            if premium and premium.end_date and premium.end_date > now:
                premium.end_date = premium.end_date + relativedelta(months=quantity)
                premium.duration_months = int(premium.duration_months or 0) + quantity
                db.commit()
                logger.info(
                    f"Extended premium for user {entity_id} by {quantity} month(s). New expiry: {premium.end_date}"
                )
            else:
                new_premium = UserPremium(
                    user_id=entity_id,
                    start_date=now,
                    end_date=now + relativedelta(months=quantity),
                    duration_months=quantity,
                    is_active=True,
                )
                db.add(new_premium)
                db.commit()
                logger.info(
                    f"Activated premium for user {entity_id} for {quantity} month(s). Expires: {new_premium.end_date}"
                )

        else:
            logger.warning(f"Unknown payment_for action: {action}")

    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        logging.exception(f"Error in complate_payment: {str(e)}")


# ses = SessionLocal()
# payment = ses.query(ClickPayment).first()
# complate_payment(payment, ses)
