import os
import uuid
import logging
from pathlib import Path

import boto3

logger = logging.getLogger(__name__)

# Initialize the S3 client once so that successive uploads are fast
s3_client = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("VITE_AWS_ACCESS_KEY"),
    aws_secret_access_key=os.getenv("VITE_AWS_SECRET_KEY"),
    region_name=os.getenv("VITE_AWS_REGION"),
)

def _get_content_type(file_extension: str) -> str:
    """Return the MIME type based on a file extension.

    Falls back to ``application/octet-stream`` when the extension is not
    recognised.
    """
    content_type_map = {
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".pdf": "application/pdf",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".json": "application/json",
    }
    return content_type_map.get(file_extension.lower(), "application/octet-stream")


def upload_to_s3(file_path: str, *, prefix: str = "processed-documents/") -> tuple[str, str]:
    """Upload ``file_path`` to the configured S3 bucket.

    Parameters
    ----------
    file_path: str
        Absolute or relative path to the file that should be uploaded.
    prefix: str, optional
        Key prefix inside the bucket. Defaults to ``processed-documents/``.

    Returns
    -------
    tuple[str, str]
        (public_url, generated_filename)

    Raises
    ------
    ValueError
        When the bucket environment variable is missing.
    FileNotFoundError
        When *file_path* does not exist.
    botocore.exceptions.BotoCoreError
        When the upload fails for any reason.
    """
    bucket_name = os.getenv("VITE_S3_BUCKET_NAME")
    if not bucket_name:
        raise ValueError("AWS bucket name not configured (VITE_S3_BUCKET_NAME)")

    path_obj = Path(file_path)
    if not path_obj.exists():
        raise FileNotFoundError(f"{file_path} does not exist")

    file_extension = path_obj.suffix or ""
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_key = f"{prefix}{unique_filename}"

    content_type = _get_content_type(file_extension)

    logger.info("Uploading %s to bucket %s as %s", path_obj.name, bucket_name, file_key)

    with open(path_obj, "rb") as file_obj:
        s3_client.upload_fileobj(
            file_obj,
            bucket_name,
            file_key,
            ExtraArgs={"ContentType": content_type},
        )

    s3_url = f"https://{bucket_name}.s3.amazonaws.com/{file_key}"
    logger.info("Upload successful: %s", s3_url)
    Path(file_path).unlink(missing_ok=True)
    logger.info("File deleted from local storage")

    return s3_url, unique_filename 