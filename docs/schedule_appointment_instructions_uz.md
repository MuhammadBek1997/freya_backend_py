Shedul yaratish, appointment yaratish va appointment statusini yangilash bo‘yicha amaliy ko‘rsatmalar

Quyidagi qadamlar `http://localhost:8000/api` bazaviy URL bo‘yicha yozilgan. Har bir so‘rovda `Authorization: Bearer <TOKEN>` va `X-User-language: uz` headerlarini qo‘shing.

Oldindan shartlar
- Mavjud `superadmin` akkaunti bo‘lishi va unga kirish (token olish) kerak.
- Salon mavjud bo‘lsa uning `salon_id` qiymatini bilib oling. Agar yo‘q bo‘lsa, pastdagi “Salon yaratish” qadamini bajaring.
- Admin roli aynan `admin` bo‘lishi shart (private_admin yoki superadmin emas). Aks holda xodim yaratish 403 qaytaradi.

1) Superadmin bilan login qilish
- Endpoint: `POST /api/auth/superadmin/login`
- Body:
```
{
  "username": "<SUPERADMIN_USERNAME>",
  "password": "<SUPERADMIN_PASSWORD>"
}
```
- Javobdan `token` ni oling: `<SUPERADMIN_TOKEN>`

2) Admin yaratish (role = "admin")
- Endpoint: `POST /api/auth/admin/create`
- Header: `Authorization: Bearer <SUPERADMIN_TOKEN>`
- Body (salon tayyor bo‘lsa `salon_id` ni kiriting, bo‘lmasa keyinroq salon yaratib adminga salon id berish zarur):
```
{
  "username": "salon_admin",
  "email": "admin@example.com",
  "password": "Admin@123",
  "full_name": "Salon Admin",
  "role": "admin",
  "salon_id": "<EXISTING_SALON_ID_OR_NULL>"
}
```

3) Admin bilan login qilish
- Endpoint: `POST /api/auth/admin/login`
- Body:
```
{
  "username": "salon_admin",
  "password": "Admin@123"
}
```
- Javobdan `token` ni oling: `<ADMIN_TOKEN>` va agar mavjud bo‘lsa `salon_id` ni ham ko‘ring.

4) Salon yaratish (agar hali yo‘q bo‘lsa)
- Endpoint: `POST /api/salons/`
- Header: `Authorization: Bearer <ADMIN_TOKEN>`
- Minimal namunaviy body:
```
{
  "salon_name": "Freya Test Salon",
  "salon_phone": "+998901234567",
  "salon_instagram": "freya_salon",
  "salon_rating": 5,
  "salon_types": [],
  "location": {"latitude": 41.0, "longitude": 64.0},
  "salon_comfort": [],
  "is_private": false,
  "description_uz": "Test salon", "description_ru": "Test", "description_en": "Test",
  "address_uz": "Toshkent", "address_ru": "Tashkent", "address_en": "Tashkent",
  "orientation_uz": "Markaz", "orientation_ru": "Center", "orientation_en": "Center"
}
```
- Javobdan `salon_id` ni oling: `<SALON_ID>`.
- Eslatma: Adminning `salon_id` maydonini ushbu salon bilan bog‘lash talab qilinadi. Agar admin yaratilganda `salon_id` kiritilmagan bo‘lsa, admin profilingizni yangilash yoki adminni qayta yaratishda `salon_id` ko‘rsatish zarur. (Agar adminni yangilash endpointi bo‘lmasa, eng sodda yo‘l: adminni `salon_id` bilan qayta yaratish.)

5) Xodim (employee) yaratish
- Endpoint: `POST /api/employees/`
- Header: `Authorization: Bearer <ADMIN_TOKEN>`
- Muhim: Admin roli `admin` va adminning `salon_id` to‘ldirilgan bo‘lishi shart.
- Body:
```
{
  "employee_name": "Jane Doe",
  "employee_phone": "+998909999999",
  "employee_email": "jane@example.com",
  "role": "employee",
  "username": "jane_employee",
  "profession": "Hairdresser",
  "employee_password": "Emp@12345"
}
```
- Javobdan `id` ni oling: `<EMPLOYEE_ID>` va keyin xodim bilan login qiling.

6) Xodim bilan login qilish
- Endpoint: `POST /api/auth/employee/login`
- Body:
```
{
  "username": "jane_employee",
  "password": "Emp@12345"
}
```
- Javobdan `token` ni oling: `<EMPLOYEE_TOKEN>`

7) Schedule (jadval) yaratish
- Endpoint: `POST /api/schedules/`
- Header: `Authorization: Bearer <ADMIN_TOKEN>` (yoki foydalanuvchi/employee token — endpoint `get_current_user` bilan himoyalangan)
- Body (oddiy namunaviy jadval):
```
{
  "salon_id": "<SALON_ID>",
  "name": "Kundalik qabul",
  "date": "2025-10-07",
  "start_time": "09:00:00",
  "end_time": "12:00:00",
  "repeat": false,
  "employee_list": ["<EMPLOYEE_ID>"],
  "price": 150000,
  "is_active": true
}
```
- Javobdan `id` ni oling: `<SCHEDULE_ID>`

8) Shu jadval asosida appointment yaratish
- Endpoint: `POST /api/appointments/`
- Header: `Authorization: Bearer <ADMIN_TOKEN>` yoki `Bearer <USER_TOKEN>`; endpoint `get_current_user_optional` bo‘lib, foydalanuvchi bo‘lsa `user_id` yoziladi.
- Body:
```
{
  "schedule_id": "<SCHEDULE_ID>",
  "user_name": "Mijoz Ismi",
  "phone_number": "+998901112233",
  "application_date": "2025-10-07",
  "application_time": "10:00:00",
  "service_name": "Soch olish",
  "service_price": 150000,
  "notes": "Qo‘shimcha izoh"
}
```
- Javobdan `id` ni oling: `<APPOINTMENT_ID>` va status default `pending` bo‘ladi.

9) Appointment statusini yangilash (faqat xodim)
- Endpoint: `PATCH /api/appointments/<APPOINTMENT_ID>/status`
- Header: `Authorization: Bearer <EMPLOYEE_TOKEN>`
- Body: statuslardan biri `pending | cancelled | accepted | ignored | done`
```
{
  "status": "accepted",
  "notes": "Qabul qilindi"
}
```
- Natija: `200 OK`, appointment `status` yangilanadi. Admin, superadmin va oddiy user uchun bu endpoint 403 qaytaradi.

Qo‘shimcha maslahatlar
- 403 xato bo‘lsa, tekshiring: (a) admin roli `admin` ekanligi; (b) adminning `salon_id` mavjudligi; (c) employee login tokeni bilan status yangilayotganligi.
- Schedule yaratishda `start_time < end_time` bo‘lishi shart.
- Appointment yaratishda schedule mavjudligi va unga bog‘liq salon mavjudligi tekshiriladi.


