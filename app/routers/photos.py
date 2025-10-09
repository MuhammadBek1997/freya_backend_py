from typing import Union
from fastapi import APIRouter, Depends, HTTPException, Header, UploadFile, File, status, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os
import uuid
from app.database import get_db
from app.i18nMini import get_translation
from app.middleware.auth import get_current_user
from app.models.photo import Photo
from app.schemas.photo import PhotoUploadResponse

router = APIRouter(prefix="/photos", tags=["Photos"])


@router.post("/upload", response_model=PhotoUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_photos(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """Rasmlar yuklash endpointi. Superadmin ruxsat etilmaydi."""
    try:
        role = getattr(current_user, "role", None)
        if role == "superadmin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=get_translation(language, "errors.403")
            )

        # Faoliyat ko'rish: faqat tasvir fayllariga ruxsat
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=get_translation(language, "errors.400")
            )

        photos_dir = os.path.join(os.getcwd(), "photos")
        os.makedirs(photos_dir, exist_ok=True)

        # Fayl nomini generatsiya qilish (uuid + original extension)
        orig_name = file.filename or "image"
        _, ext = os.path.splitext(orig_name)
        if not ext:
            # MIME turidan extensionni taxmin qilish (minimal)
            ext = ".jpg" if file.content_type == "image/jpeg" else ".png"
        safe_name = f"{uuid.uuid4().hex}{ext}"
        save_path = os.path.join(photos_dir, safe_name)

        # Diskka saqlash
        with open(save_path, "wb") as out:
            content = await file.read()
            out.write(content)

        # To'liq URL yasash
        base = str(request.base_url).rstrip("/")
        url = f"{base}/api/photos/{safe_name}"

        # DB yozuvini saqlash
        photo = Photo(
            filename=safe_name,
            url=url,
            uploader_id=getattr(current_user, "id"),
            uploader_role=role or "user",
        )
        db.add(photo)
        db.commit()

        return PhotoUploadResponse(url=url)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Upload error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=get_translation(language, "errors.500")
        )

@router.get("/{filename}")
async def get_photo(filename: str):
    """Fayl nomi orqali rasmni ochish."""
    photos_dir = os.path.join(os.getcwd(), "photos")
    file_path = os.path.join(photos_dir, filename)
    
    if not os.path.isfile(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Rasm topilmadi"
        )
    
    return FileResponse(file_path)
