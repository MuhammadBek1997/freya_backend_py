import asyncio
from datetime import datetime, timedelta, time as dtime
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.schedule import Schedule
from app.routers.mobile_schedules import create_appointment, MobileAppointmentCreate

SCHEDULE_ID = "e78d69da-833d-4a1d-83e2-648b671b3085"
EMPLOYEE_ID = "4a8f338a-d03e-42a1-93b6-ba73d0cb0dbb"
PHONE = "+998901234567"
USER_NAME = "Booknow Tester"


def main():
    session: Session = SessionLocal()
    try:
        schedule = session.query(Schedule).filter(Schedule.id == SCHEDULE_ID).first()
        if not schedule:
            print("[ERROR] Schedule not found:", SCHEDULE_ID)
            return
        print("[INFO] Schedule:", {
            "id": str(schedule.id),
            "salon_id": str(schedule.salon_id),
            "date": schedule.date.isoformat() if schedule.date else None,
            "start_time": schedule.start_time.strftime('%H:%M') if schedule.start_time else None,
            "end_time": schedule.end_time.strftime('%H:%M') if schedule.end_time else None,
        })

        # pick a time within schedule range
        app_time = schedule.start_time or dtime(10, 0)
        if schedule.start_time and schedule.end_time:
            dt_start = datetime.combine(schedule.date, schedule.start_time)
            dt_end = datetime.combine(schedule.date, schedule.end_time)
            candidate = dt_start + timedelta(minutes=30)
            if candidate < dt_end:
                app_time = candidate.time()

        data = MobileAppointmentCreate(
            salon_id=str(schedule.salon_id),
            schedule_id=SCHEDULE_ID,
            employee_id=EMPLOYEE_ID,
            application_date=schedule.date,
            application_time=app_time,
            user_name=USER_NAME,
            phone_number=PHONE,
            only_card=False,
            payment_card_id=None,
            notes="booknow test",
        )

        # First attempt: should succeed
        print("[TEST] First booking attempt...")
        resp1 = asyncio.run(create_appointment(data, db=session, language='uz'))
        try:
            out1 = resp1.dict()
        except Exception:
            out1 = resp1.model_dump()
        print("[RESULT-1] status:", "OK")
        print("[RESULT-1] payload:", out1)

        # Second attempt on the same slot: should fail with 409
        print("[TEST] Second booking attempt (same slot, expect 409)...")
        try:
            resp2 = asyncio.run(create_appointment(data, db=session, language='uz'))
            try:
                out2 = resp2.dict()
            except Exception:
                out2 = resp2.model_dump()
            print("[RESULT-2] UNEXPECTED SUCCESS:", out2)
        except Exception as e:
            print("[RESULT-2] Expected conflict:", str(e))
    except Exception as e:
        print("[ERROR]", e)
    finally:
        session.close()


if __name__ == "__main__":
    main()