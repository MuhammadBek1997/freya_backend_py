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
            # Grant premium months to user via helper
            try:
                auto_extend_user_premium(entity_id, quantity, db)
                logger.info(
                    f"Premium processing completed via helper for user {entity_id}, months={quantity}"
                )
            except Exception as e:
                logger.error(f"Failed to auto-extend premium for user {entity_id}: {e}")

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


def deactivate_expired_premiums(db: Session) -> int:
    """Mark expired active premiums as inactive.

    Sets `is_active=False` for records where `is_active=True` and `end_date <= now`.
    Returns the number of affected rows.
    """
    logger = logging.getLogger("ClickComplete")
    now = datetime.utcnow()
    try:
        affected = (
            db.query(UserPremium)
            .filter(UserPremium.is_active == True, UserPremium.end_date <= now)
            .update({UserPremium.is_active: False}, synchronize_session=False)
        )
        db.commit()
        logger.info(f"Deactivated {affected} expired premium record(s)")
        return int(affected or 0)
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        logging.exception(f"Error deactivating expired premiums: {str(e)}")
        return 0


def auto_extend_user_premium(user_id: str, months: int, db: Session) -> None:
    """Auto-extend a user's premium by given months or create a new active period.

    - If there is an active premium (is_active=True and not expired), extend its end_date and duration_months
    - Else, create a new premium record starting now for `months`
    """
    logger = logging.getLogger("ClickComplete")

    if months <= 0:
        raise ValueError("months must be a positive integer")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError(f"User not found: {user_id}")

    now = datetime.utcnow()

    # Ensure expired premiums are marked inactive before extending
    try:
        db.query(UserPremium).filter(
            UserPremium.user_id == user_id,
            UserPremium.is_active == True,
            UserPremium.end_date <= now,
        ).update({UserPremium.is_active: False}, synchronize_session=False)
        db.commit()
    except Exception:
        # Non-critical: proceed to extend/create
        try:
            db.rollback()
        except Exception:
            pass

    premium = (
        db.query(UserPremium)
        .filter(UserPremium.user_id == user_id, UserPremium.is_active == True)
        .order_by(UserPremium.end_date.desc())
        .first()
    )

    if premium and premium.end_date and premium.end_date > now:
        premium.end_date = premium.end_date + relativedelta(months=months)
        premium.duration_months = int(premium.duration_months or 0) + months
        db.commit()
        logger.info(
            f"Extended premium for user {user_id} by {months} month(s). New expiry: {premium.end_date}"
        )
    else:
        new_premium = UserPremium(
            user_id=user_id,
            start_date=now,
            end_date=now + relativedelta(months=months),
            duration_months=months,
            is_active=True,
        )
        db.add(new_premium)
        db.commit()
        logger.info(
            f"Activated premium for user {user_id} for {months} month(s). Expires: {new_premium.end_date}"
        )
