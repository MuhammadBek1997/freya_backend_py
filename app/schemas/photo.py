from pydantic import BaseModel


class PhotoUploadResponse(BaseModel):
    url: str