from contextlib import asynccontextmanager
from fastapi import FastAPI
from apscheduler.schedulers.background import BackgroundScheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    # Create database tables
    try:
        Base.metadata.create_all(bind=engine)
        print("Database tables created")
    except Exception as e:
        print(f"[Startup] Skipping table creation due to DB error: {e}")
    # Ensure default superadmin exists after tables are created
    try:
        from app import check_and_create_admin
        check_and_create_admin()
    except Exception:
        # Avoid breaking startup if admin creation fails
        pass

    # APScheduler: deactivate expired premiums periodically
    try:
        scheduler = BackgroundScheduler(timezone="UTC")

        def _deactivate_job():
            db = SessionLocal()
            try:
                count = deactivate_expired_premiums(db)
                if count:
                    print(f"[Scheduler] Deactivated {count} expired premium(s)")
            finally:
                try:
                    db.close()
                except Exception:
                    pass

        # Run daily at 00:00 (UTC) and also at app startup once
        _deactivate_job()
        scheduler.add_job(_deactivate_job, CronTrigger(hour=8, minute=0))
        scheduler.start()
        app.state.scheduler = scheduler
    except Exception as e:
        print(f"[Startup] Failed to start APScheduler: {e}")
    yield
    # Shutdown
    try:
        sched = getattr(app.state, "scheduler", None)
        if sched:
            sched.shutdown(wait=False)
    except Exception:
        pass

app = FastAPI(lifespan=lifespan)