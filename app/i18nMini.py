messages = {
    "uz": {
        "admin": {
            "makeTop": "{name} saloni {duration} kunga top qilindi",
            "removeTop": "{name} saloni topdan olindi",
        },
        "appointment": {
            "created": "Uchrashuv muvaffaqiyatli yaratildi",
            "updated": "Uchrashuv muvaffaqiyatli yangilandi",
            "cancelled": "Uchrashuv muvaffaqiyatli bekor qilindi",
            "deleted": "Uchrashuv muvaffaqiyatli o'chirildi",
            "completed": "Uchrashuv muvaffaqiyatli yakunlandi",
            "inProgress": "Uchrashuv jarayonda",
        },
        "auth": {
            "invalidCredentials": "Noto'g'ri login yoki parol",
            "inactiveUser": "Foydalanuvchi faol emas",
            "userNotFound": "Foydalanuvchi topilmadi",
            "emailExists": "Bu email allaqachon ro'yxatdan o'tgan",
            "phoneExists": "Bu telefon raqam allaqachon ro'yxatdan o'tgan",
            "userExists": "Bu foydalanuvchi allaqachon ro'yxatdan o'tgan",
            "userCreated": "Foydalanuvchi muvaffaqiyatli yaratildi",
            "userUpdated": "Foydalanuvchi muvaffaqiyatli yangilandi",
            "userDeleted": "Foydalanuvchi muvaffaqiyatli o'chirildi",
            "userActivated": "Foydalanuvchi muvaffaqiyatli faollashtirildi",
            "userDeactivated": "Foydalanuvchi muvaffaqiyatli faollashtirildi",
            "userDeactivated": "Foydalanuvchi muvaffaqiyatli faollashtirildi",
            "messageSent": "Xabar muvaffaqiyatli yuborildi",
            "invalidVerificationCode": "Noto'g'ri tasdiqlash kodi",
            "verificationCodeSent": "Tasdiqlash kodi muvaffaqiyatli yuborildi",
            "passwordReset": "Parol muvaffaqiyatli tiklandi",
            "codeExpired": "Tasdiqlash kodi muddati o'tgan",
            "codeNotsent": "Tasdiqlash kodi yuborilmadi",
            "userVerified": "Telefon raqam tasdiqlandi",
            "success": "Muvaffaqiyatli bajarildi",
        },
        "errors": {
            "500": "Server xatosi",
            "404": "Topilmadi",
            "403": "Ruxsat yo'q",
            "400": "Noto'g'ri so'rov",
        },
        "success": "Muvaffaqiyatli bajarildi",
    },
    "ru": {
        "admin": {
            "makeTop": "Салон {name} поднят в топ на {duration} дней",
            "removeTop": "Салон {name} убран из топа",
        },
        "appointment": {
            "created": "Встреча успешно создана",
            "updated": "Встреча успешно обновлена",
            "cancelled": "Встреча успешно отменена",
            "deleted": "Встреча успешно удалена",
            "completed": "Встреча успешно завершена",
            "inProgress": "Встреча в процессе",
        },
        "auth": {
            "invalidCredentials": "Неверный логин или пароль",
            "inactiveUser": "Пользователь неактивен",
            "userNotFound": "Пользователь не найден",
            "emailExists": "Этот email уже зарегистрирован",
            "phoneExists": "Этот номер телефона уже зарегистрирован",
            "userExists": "Этот пользователь уже зарегистрирован",
            "userCreated": "Пользователь успешно создан",
            "userUpdated": "Пользователь успешно обновлен",
            "userDeleted": "Пользователь успешно удален",
            "userActivated": "Пользователь успешно активирован",
            "userDeactivated": "Пользователь успешно деактивирован",
            "messageSent": "Сообщение успешно отправлено",
            "invalidVerificationCode": "Неверный код подтверждения",
            "verificationCodeSent": "Код подтверждения успешно отправлен",
            "passwordReset": "Пароль успешно восстановлен",
            "codeExpired": "Срок действия кода подтверждения истёк",
            "codeNotsent": "Код подтверждения не был отправлен",
            "userVerified": "Номер телефона подтвержден",
            "success": "Успешно выполнено",
        },
        "errors": {
            "500": "Ошибка сервера",
            "404": "Не найдено",
            "403": "Нет доступа",
            "400": "Неверный запрос",
        },
        "success": "Успешно выполнено",
    },
    "en": {
        "admin": {
            "makeTop": "{name} salon has been placed on top for {duration} days",
            "removeTop": "{name} salon has been removed from top",
        },
        "appointment": {
            "created": "Appointment successfully created",
            "updated": "Appointment successfully updated",
            "cancelled": "Appointment successfully cancelled",
            "deleted": "Appointment successfully deleted",
            "completed": "Appointment successfully completed",
            "inProgress": "Appointment in progress",
        },
        "auth": {
            "invalidCredentials": "Invalid login or password",
            "inactiveUser": "User is inactive",
            "userNotFound": "User not found",
            "emailExists": "This email is already registered",
            "phoneExists": "This phone number is already registered",
            "userExists": "This user is already registered",
            "userCreated": "User successfully created",
            "userUpdated": "User successfully updated",
            "userDeleted": "User successfully deleted",
            "userActivated": "User successfully activated",
            "userDeactivated": "User successfully deactivated",
            "messageSent": "Message successfully sent",
            "invalidVerificationCode": "Invalid verification code",
            "verificationCodeSent": "Verification code successfully sent",
            "passwordReset": "Password successfully reset",
            "codeExpired": "Verification code has expired",
            "codeNotsent": "Verification code not sent",
            "userVerified": "Phone number verified",
            "success": "Successfully completed",
        },
        "errors": {
            "500": "Server error",
            "404": "Not found",
            "403": "Forbidden",
            "400": "Bad request",
        },
        "success": "Successfully completed",
    },
}


def get_translation(language: str, section: str = None):
    keys = section.split(".") if section else []
    current = messages
    if language not in current:
        return None
    current = current[language]
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return None
    return current
