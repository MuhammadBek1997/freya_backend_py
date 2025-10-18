import asyncio
from app.database import SessionLocal
from app.routers.mobile_schedules import get_mobile_schedules_by_employee

async def main():
    db = SessionLocal()
    try:
        employee_id = "2b5f1c72-51fd-4b59-98fd-9c41fcae7c2c"
        start_date = "2024-10-14"
        resp = await get_mobile_schedules_by_employee(
            employee_id=employee_id,
            start_date=start_date,
            page=1,
            limit=7,
            db=db,
            language=None,
        )
        print(resp)
    finally:
        db.close()

asyncio.run(main())
