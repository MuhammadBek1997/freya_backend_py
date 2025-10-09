import boto3
import os
from dotenv import load_dotenv
from botocore.exceptions import NoCredentialsError

load_dotenv()

AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")
S3_BUCKET = os.getenv("AWS_S3_BUCKET_NAME")

s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=AWS_REGION
)

def upload_file_to_s3(file_obj, filename: str, folder: str = ""):
    """Faylni S3 bucketga yuklaydi va URL qaytaradi."""
    try:
        key = f"{folder}/{filename}" if folder else filename
        s3_client.upload_fileobj(file_obj, S3_BUCKET, key, ExtraArgs={"ACL": "public-read"})
        file_url = f"https://{S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{key}"
        return file_url
    except NoCredentialsError:
        raise Exception("AWS Malumotlari topilmadi. .env faylni tekshiring.")
