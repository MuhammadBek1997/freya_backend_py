from datetime import datetime
from dateutil.relativedelta import relativedelta
import logging
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.config import settings


from app.config import Settings
from app.database import SessionLocal
from app.models.payment import ClickPayment
from app.models.payment_card import PaymentCard
from app.models.user import User
from app.models.employee import EmployeePostLimit
from app.models.user_premium import UserPremium
from app.services.Click import PaymentStatus


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
                limits = EmployeePostLimit(
                    employee_id=entity_id, free_posts_used=0, total_paid_posts=0
                )
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

    For users without auto-pay: deactivates expired premiums immediately
    For users with auto-pay: deactivates expired premiums so they can be processed again tomorrow
    Returns the number of affected rows.
    """
    logger = logging.getLogger("ClickComplete")
    now = datetime.utcnow()
    try:
        # Сначала деактивируем все дублирующиеся активные подписки
        users_with_multiple = (
            db.query(UserPremium.user_id)
            .filter(UserPremium.is_active == True)
            .group_by(UserPremium.user_id)
            .having(db.func.count(UserPremium.id) > 1)
            .all()
        )

        for user_id in users_with_multiple:
            # Оставляем только самую свежую подписку активной
            premiums = (
                db.query(UserPremium)
                .filter(
                    UserPremium.user_id == user_id[0], UserPremium.is_active == True
                )
                .order_by(UserPremium.end_date.desc())
                .all()
            )
            # Деактивируем все кроме последней
            for premium in premiums[1:]:
                premium.is_active = False
            db.commit()
            logger.warning(f"Fixed multiple active premiums for user {user_id[0]}")

        # Получаем все истекшие активные премиумы
        expired_premiums = (
            db.query(UserPremium)
            .filter(UserPremium.is_active == True, UserPremium.end_date <= now)
            .all()
        )

        affected = 0
        for premium in expired_premiums:
            # Деактивируем все истекшие подписки
            premium.is_active = False
            affected += 1

            # Если у пользователя есть автопродление — подготовим платеж и попробуем провести его
            if premium.user.auto_pay_for_premium and premium.user.card_for_auto_pay_id:
                quantity_months = int(premium.duration_months or 1)
                amount_for_month = Settings.AMOUNT_FOR_PREMIUM  # Example amount for 1 month

                payment = ClickPayment(
                    payment_for=f"premium_{premium.user.id}_{quantity_months}",
                    amount=str(amount_for_month * quantity_months),
                    status="created",
                    payment_card_id=premium.user.card_for_auto_pay_id,
                )
                db.add(payment)
                db.commit()
                db.refresh(payment)

                get_card = (
                    db.query(PaymentCard)
                    .filter(
                        PaymentCard.id == premium.user.card_for_auto_pay_id,
                        PaymentCard.user_id == premium.user.id,
                        PaymentCard.is_active == True,
                        PaymentCard.is_verified == True,
                    )
                    .first()
                )
                if not get_card:
                    # Карту не нашли/неактивна — пометим платеж как ошибочный и продолжим
                    payment.status = PaymentStatus.ERROR.value
                    db.commit()
                    logger.warning(
                        f"Card not found or inactive for user {premium.user.id}; payment recorded as error. Will try next check."
                    )
                    continue

                # Пометим платеж как в ожидании и попытаемся провести
                payment.status = PaymentStatus.PENDING.value
                db.commit()

                try:
                    result = settings.click_provider.payment_with_token(
                        card_token=get_card.card_token,
                        amount=payment.amount,
                        merchant_trans_id=payment.id,
                    )
                except Exception as e:
                    payment.status = PaymentStatus.ERROR.value
                    db.commit()
                    logger.error(f"Error while calling payment provider for user {premium.user.id}: {e}")
                    # Не прерываем обработку: на следующей проверке попробуем снова
                    continue

                if result.get("error_code"):
                    payment.status = PaymentStatus.ERROR.value
                    db.commit()
                    logger.warning(
                        f"Payment provider returned error for user {premium.user.id}: {result.get('error_code')} - {result.get('error_note')}"
                    )
                    # Попробуем снова при следующей проверке
                    continue

                logger.info(f"Payment succeeded and recorded for user {premium.user.id}; extending premium.")


        db.commit()
        logger.info(f"Deactivated {affected} expired premium record(s)")
        return affected
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        logging.exception(f"Error deactivating expired premiums: {str(e)}")
        return 0


def auto_extend_user_premium(user_id: str, months: int, db: Session) -> None:
    """Auto-extend a user's premium by given months or create a new active period.

    - If there is an active non-expired premium, extends its duration
    - If there are multiple active premiums, keeps the latest and extends it
    - If no active non-expired premium exists, creates a new one
    """
    logger = logging.getLogger("ClickComplete")

    if months <= 0:
        raise ValueError("months must be a positive integer")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError(f"User not found: {user_id}")

    now = datetime.utcnow()

    # Получаем все активные подписки пользователя
    active_premiums = (
        db.query(UserPremium)
        .filter(UserPremium.user_id == user_id, UserPremium.is_active == True)
        .order_by(UserPremium.end_date.desc())
        .all()
    )

    # Если есть несколько активных подписок
    if len(active_premiums) > 1:
        # Оставляем только самую свежую, остальные деактивируем
        latest_premium = active_premiums[0]
        for premium in active_premiums[1:]:
            premium.is_active = False
        db.commit()
        logger.warning(
            f"Deactivated {len(active_premiums)-1} duplicate premium(s) for user {user_id}"
        )

        # Используем самую свежую подписку для продления
        if latest_premium.end_date > now:
            latest_premium.end_date = latest_premium.end_date + relativedelta(
                months=months
            )
            latest_premium.duration_months = (
                int(latest_premium.duration_months or 0) + months
            )
            db.commit()
            logger.info(
                f"Extended existing premium for user {user_id} by {months} month(s). New expiry: {latest_premium.end_date}"
            )
            return

    # Если есть одна активная неистекшая подписка
    elif len(active_premiums) == 1 and active_premiums[0].end_date > now:
        active_premiums[0].end_date = active_premiums[0].end_date + relativedelta(
            months=months
        )
        active_premiums[0].duration_months = (
            int(active_premiums[0].duration_months or 0) + months
        )
        db.commit()
        logger.info(
            f"Extended existing premium for user {user_id} by {months} month(s). New expiry: {active_premiums[0].end_date}"
        )
        return

    # Деактивируем все оставшиеся/истекшие подписки и создаем новую
    db.query(UserPremium).filter(
        UserPremium.user_id == user_id, UserPremium.is_active == True
    ).update({UserPremium.is_active: False}, synchronize_session=False)
    db.commit()

    # Создаем новую подписку
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
