import psycopg2
from app.config import settings

def check_postgresql_tables():
    """PostgreSQL bazada jadvallarni tekshirish"""
    try:
        # Database URL dan connection parametrlarini ajratib olish
        db_url = settings.database_url
        print(f"Database URL: {db_url}")
        
        # psycopg2 bilan ulanish
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        # Barcha jadvallarni ko'rish
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        tables = cursor.fetchall()
        
        print("PostgreSQL bazada mavjud jadvallar:")
        for table in tables:
            print(f"  {table[0]}")
        
        # Salon jadvali bor bo'lsa, uning strukturasini ko'rish
        salon_tables = [table[0] for table in tables if 'salon' in table[0].lower()]
        
        for table_name in salon_tables:
            print(f"\n{table_name} jadvalining ustunlari:")
            cursor.execute(f"""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_name = '{table_name}'
                ORDER BY ordinal_position;
            """)
            columns = cursor.fetchall()
            for column in columns:
                print(f"  {column[0]} - {column[1]} ({'NULL' if column[2] == 'YES' else 'NOT NULL'})")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Xatolik yuz berdi: {e}")

if __name__ == "__main__":
    check_postgresql_tables()