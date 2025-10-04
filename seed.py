import random
import uuid
from typing import List

from app.database import SessionLocal
from app.models.salon import Salon
from app.models.admin import Admin
from app.models.employee import Employee
from app.auth.jwt_utils import JWTUtils


def seed_salons_admins_employees(num_salons: int = 10):
    db = SessionLocal()
    try:
        password_plain = "12345678"
        password_hash = JWTUtils.hash_password(password_plain)

        created_salons: List[Salon] = []
        created_admins: int = 0
        created_employees: int = 0

        for i in range(1, num_salons + 1):
            salon = Salon(
                salon_name=f"Salon {i}",
                salon_phone=f"+99890{str(1000000 + i).zfill(7)}",
                salon_instagram=f"@salon_{i}",
                is_active=True,
                description_uz=f"Salon {i} tavsifi",
                address_uz=f"Toshkent sh., Chilonzor {i}",
            )
            db.add(salon)
            db.flush()  # get salon.id

            # Varying counts per salon
            admin_count = random.randint(1, 3)
            employee_count = random.randint(2, 7)

            # Create admins
            for a in range(1, admin_count + 1):
                username = f"admin_{i}_{a}"
                email = f"admin_{i}_{a}@example.com"
                phone = f"+99891{str(1000000 + i * 10 + a).zfill(7)}"

                admin = Admin(
                    salon_id=salon.id,
                    username=username,
                    email=email,
                    password_hash=password_hash,
                    full_name=f"Admin {i}-{a}",
                    phone=phone,
                    role="admin",
                    is_active=True,
                )
                db.add(admin)
                created_admins += 1

            # Create employees
            for e in range(1, employee_count + 1):
                username = f"employee_{i}_{e}"
                email = f"employee_{i}_{e}@example.com"
                phone = f"+99893{str(1000000 + i * 10 + e).zfill(7)}"

                employee = Employee(
                    salon_id=salon.id,
                    name=f"Employee {i}-{e}",
                    surname="",
                    position="Stylist",
                    phone=phone,
                    email=email,
                    role="employee",
                    profession="Hair",
                    username=username,
                    employee_password=password_hash,
                    is_active=True,
                )
                db.add(employee)
                created_employees += 1

            created_salons.append(salon)

        db.commit()

        print(
            f"Seed completed: salons={len(created_salons)}, admins={created_admins}, employees={created_employees}"
        )
    except Exception as e:
        db.rollback()
        print(f"Seed error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_salons_admins_employees(10)


def seed_fixed_salons_admins_employees(num_salons: int = 5):
    """
    Create exactly `num_salons` salons each with 1 admin and 1 employee.
    Admin usernames: admin_1..admin_N
    Employee usernames: employee_1..employee_N
    Password: 12345678
    """
    db = SessionLocal()
    try:
        password_plain = "12345678"
        password_hash = JWTUtils.hash_password(password_plain)

        admin_usernames = []
        employee_usernames = []

        for i in range(1, num_salons + 1):
            salon = Salon(
                salon_name=f"Salon {i}",
                salon_phone=f"+99890{str(1000000 + i).zfill(7)}",
                salon_instagram=f"@salon_{i}",
                is_active=True,
                description_uz=f"Salon {i} tavsifi",
                address_uz=f"Toshkent sh., Chilonzor {i}",
                # Provide defaults for JSON fields to avoid nulls
                salon_types=[
                    {"type": "Beauty Salon", "selected": True},
                    {"type": "Fitness", "selected": False},
                ],
                location={"lat": 41, "lng": 64},
                salon_comfort=[
                    {"name": "parking", "isActive": False},
                    {"name": "water", "isActive": False},
                ],
            )
            db.add(salon)
            db.flush()  # ensure salon.id

            # One admin per salon
            admin_username = f"admin_{i}"
            admin = Admin(
                salon_id=salon.id,
                username=admin_username,
                email=f"{admin_username}@example.com",
                password_hash=password_hash,
                full_name=f"Admin {i}",
                phone=f"+99891{str(1000000 + i).zfill(7)}",
                role="admin",
                is_active=True,
            )
            db.add(admin)
            admin_usernames.append(admin_username)

            # One employee per salon
            employee_username = f"employee_{i}"
            employee = Employee(
                salon_id=salon.id,
                name=f"Employee {i}",
                surname="",
                position="Stylist",
                phone=f"+99893{str(1000000 + i).zfill(7)}",
                email=f"{employee_username}@example.com",
                role="employee",
                profession="Hair",
                username=employee_username,
                employee_password=password_hash,
                is_active=True,
            )
            db.add(employee)
            employee_usernames.append(employee_username)

        db.commit()

        print(
            f"Seeded {num_salons} salons with 1 admin and 1 employee each."
        )
        print("Admin usernames:", ", ".join(admin_usernames))
        print("Employee usernames:", ", ".join(employee_usernames))
    except Exception as e:
        db.rollback()
        print(f"Seed error: {e}")
        raise
    finally:
        db.close()