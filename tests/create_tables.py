from app.database import engine, Base
from app.models import *

def create_tables():
    """Database jadvallarini yaratish"""
    try:
        print("Database jadvallarini yaratish boshlandi...")
        Base.metadata.create_all(bind=engine)
        print("Barcha jadvallar muvaffaqiyatli yaratildi!")
    except Exception as e:
        print(f"Xatolik yuz berdi: {e}")

if __name__ == "__main__":
    create_tables()