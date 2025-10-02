# API Endpoints Checklist

## Authentication
- [x] `POST /api/auth/superadmin/login` - Superadmin login
- [x] `POST /api/auth/admin/login` - Admin login
- [x] `POST /api/auth/admin/create` - Create admin (superadmin only) 🔒
- [x] `POST /api/auth/employee/login` - Employee login
- [x] `GET /api/auth/admin/profile` - Get admin profile 🔒

## Admin
- [x] `POST /api/admin/salon/top` - Set salon top status 🔒
- [x] `GET /api/admin/salons/top` - Get top salons list 🔒
- [x] `GET /api/admin/salon/{salon_id}/top-history` - Get salon top history 🔒
- [x] `GET /api/admin/salons` - Get all salons (pagination) 🔒
- [x] `GET /api/admin/my-salon` - Get my salon 🔒


## Users
- [x] `POST /api/users/register/step1` - Registration step 1 (phone + password)
- [x] `POST /api/users/verify-phone` - Verify phone number
- [x] `POST /api/users/register/step2` - Registration step 2 (username + email)
- [x] `POST /api/users/login` - User login
- [x] `POST /api/users/password-reset/send-code` - Send password reset code
- [x] `POST /api/users/reset-password` - Reset password
- [x] `POST /api/users/phone-change/send-code` - Send phone change code 🔒
- [x] `POST /api/users/phone-change/verify` - Telefon raqamni o'zgartirishni tasdiqlash 🔒
- [ ] `DELETE /api/users/delete` - Delete user account 🔒
- [x] `PUT /api/users/update` - Update user info 🔒
- [x] `POST /api/users/generate-token` - Generate new token 🔒
- [x] `GET /api/users/location` - Get user location 🔒
- [x] `PUT /api/users/location` - Update user location 🔒
- [x] `GET /api/users/profile` - Get user profile 🔒
- [x] `POST /api/users/profile/image/upload` - Upload profile image 🔒
<!-- - [ ] `GET /api/users/profile/image` - Get profile image 🔒 -->
- [x] `DELETE /api/users/profile/image` - Delete profile image 🔒
- [x] `POST /api/users/favourites/add` - Add favourite salon 🔒
- [x] `POST /api/users/favourites/remove` - Remove favourite salon 🔒
- [ ] `GET /api/users/favourites` - Get favourite salons 🔒
- [ ] `GET /api/users/payment-cards` - Get payment cards 🔒
- [ ] `POST /api/users/payment-cards` - Add payment card 🔒
- [ ] `PUT /api/users/payment-cards/{card_id}` - Update payment card 🔒
- [ ] `DELETE /api/users/payment-cards/{card_id}` - Delete payment card 🔒
- [ ] `PUT /api/users/payment-cards/{card_id}/set-default` - Set default payment card 🔒

## Employees
- [x] `GET /api/employees/` - Get all employees (pagination)
- [x] `POST /api/employees/` - Create employee 🔒
- [x] `GET /api/employees/salon/{salon_id}` - Get employees by salon ID
- [x] `GET /api/employees/{employee_id}` - Get employee by ID (with comments & posts)
- [x] `PUT /api/employees/{employee_id}` - Update employee 🔒
- [x] `DELETE /api/employees/{employee_id}` - Delete employee (soft delete) 🔒
- [ ] `POST /api/employees/{employee_id}/comments` - Add employee comment 🔒
- [x] `POST /api/employees/{employee_id}/posts` - Add employee post 🔒
- [x] `GET /api/employees/{employee_id}/posts` - Get employee posts
- [ ] `PATCH /api/employees/{employee_id}/waiting-status` - Update employee waiting status 🔒
- [ ] `PATCH /api/employees/bulk/waiting-status` - Bulk update waiting status 🔒

## Salons
- [x] `POST /api/salons/` - Create salon 🔒
- [x] `GET /api/salons/` - Get all salons (pagination)
- [x] `GET /api/salons/{salon_id}` - Get salon by ID
- [x] `PUT /api/salons/{salon_id}` - Update salon 🔒
- [x] `DELETE /api/salons/{salon_id}` - Delete salon (soft delete) 🔒
- [ ] `POST /api/salons/{salon_id}/comments` - Add salon comment 🔒
- [ ] `GET /api/salons/nearby` - Get nearby salons
- [ ] `GET /api/salons/filter/types` - Get salons by types
- [ ] `POST /api/salons/{salon_id}/photos` - Upload salon photos 🔒
- [ ] `DELETE /api/salons/{salon_id}/photos` - Delete salon photo 🔒

## Payment
- [ ] `POST /api/payment/employee-post` - Create payment for employee post 🔒
- [ ] `POST /api/payment/user-premium` - Create payment for user premium 🔒
- [ ] `POST /api/payment/salon-top` - Create payment for salon top 🔒
- [ ] `GET /api/payment/status/{transaction_id}` - Check payment status 🔒
- [ ] `POST /api/payment/callback` - Click.uz callback
- [ ] `GET /api/payment/history` - Get payment history 🔒


## Translation
- [ ] `POST /api/translation/translate` - Translate text 🔒
- [ ] `POST /api/translation/translate-all` - Translate to all languages 🔒
- [ ] `POST /api/translation/detect-language` - Detect language 🔒
- [ ] `GET /api/translation/supported-languages` - Get supported languages
- [ ] `GET /api/translation/usage` - Get DeepL API usage info 🔒

## System
- [ ] `GET /` - Root endpoint
- [ ] `GET /health` - Health check

---

**Всего endpoints:** 78

**Легенда:**
- 🔒 - Требует Bearer token аутентификации
- [ ] - Отметьте галочкой рабочие endpoints

**Статистика:**
- Authentication: 5
- Admin: 7
- Users: 20
- Employees: 11
- Salons: 10
- Payment: 6
- SMS: 8
- Translation: 5
- System: 2