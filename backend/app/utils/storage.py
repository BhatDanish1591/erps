from __future__ import annotations

import hmac
import os
import re
import time
import uuid
from hashlib import sha256
from pathlib import Path
from typing import Optional, Tuple

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.core.config import settings
from app.core.exceptions import BadRequestException, ValidationException
from app.core.logging import get_logger

logger = get_logger(__name__)

# Allowed MIME types & extensions for LMS materials and assignment submissions
ALLOWED_EXTENSIONS = {
    # Documents
    ".pdf",
    ".doc",
    ".docx",
    ".ppt",
    ".pptx",
    ".xls",
    ".xlsx",
    ".txt",
    # Images
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".gif",
    # Video & Media
    ".mp4",
    ".webm",
    ".mov",
    # Archives
    ".zip",
    ".rar",
}

ALLOWED_MIME_PREFIXES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument",
    "application/vnd.ms-powerpoint",
    "application/vnd.ms-excel",
    "application/zip",
    "application/x-zip-compressed",
    "text/plain",
    "image/",
    "video/",
}

MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB default


class StorageService:
    def __init__(self):
        self.backend = settings.STORAGE_BACKEND
        self.local_dir = Path("uploads")
        self.local_dir.mkdir(parents=True, exist_ok=True)
        self._s3_client = None

    def _get_s3_client(self):
        if self._s3_client is not None:
            return self._s3_client

        if self.backend == "r2":
            self._s3_client = boto3.client(
                "s3",
                endpoint_url=settings.R2_ENDPOINT_URL or None,
                aws_access_key_id=settings.R2_ACCESS_KEY_ID or None,
                aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY or None,
                config=Config(signature_version="s3v4"),
                region_name="auto",
            )
        else:  # s3
            self._s3_client = boto3.client(
                "s3",
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID or None,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY or None,
                region_name=settings.AWS_REGION or "ap-south-1",
                config=Config(signature_version="s3v4"),
            )
        return self._s3_client

    def _get_bucket_name(self) -> str:
        if self.backend == "r2":
            return settings.R2_BUCKET or "edusaas-r2-bucket"
        return settings.AWS_S3_BUCKET or "edusaas-s3-bucket"

    def validate_file(
        self,
        file_name: str,
        content_type: Optional[str] = None,
        file_size_bytes: Optional[int] = None,
        max_size: int = MAX_FILE_SIZE_BYTES,
    ) -> None:
        """
        Validate file extension, MIME type, and size limits.
        """
        if not file_name:
            raise ValidationException("File name is required.", field="file_name")

        ext = Path(file_name).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValidationException(
                f"File format '{ext}' is not supported. Allowed: PDF, Word, PPT, Excel, Images, MP4, ZIP.",
                field="file_name",
            )

        if content_type:
            ct = content_type.lower()
            is_valid_mime = any(ct.startswith(prefix) for prefix in ALLOWED_MIME_PREFIXES)
            if not is_valid_mime and ct != "application/octet-stream":
                logger.warning("Uncommon MIME type encountered", content_type=content_type, file_name=file_name)

        if file_size_bytes is not None and file_size_bytes > max_size:
            max_mb = max_size // (1024 * 1024)
            raise BadRequestException(f"File size exceeds maximum permitted limit of {max_mb} MB.")

    def sanitize_filename(self, filename: str) -> str:
        clean = re.sub(r"[^\w\.-]", "_", filename)
        return clean[:100]

    def build_storage_key(self, tenant_id: uuid.UUID, folder: str, original_filename: str) -> str:
        """
        Generate tenant-partitioned object key:
        tenants/{tenant_id}/{folder}/{uuid}_{filename}
        """
        clean_name = self.sanitize_filename(original_filename)
        unique_prefix = uuid.uuid4().hex[:12]
        return f"tenants/{tenant_id}/{folder}/{unique_prefix}_{clean_name}"

    def upload_file_bytes(
        self,
        file_bytes: bytes,
        storage_key: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """
        Upload file data to active backend (S3, Cloudflare R2, or local storage).
        """
        if self.backend in ("s3", "r2") and (settings.AWS_ACCESS_KEY_ID or settings.R2_ACCESS_KEY_ID):
            try:
                client = self._get_s3_client()
                bucket = self._get_bucket_name()
                client.put_object(
                    Bucket=bucket,
                    Key=storage_key,
                    Body=file_bytes,
                    ContentType=content_type,
                )
                logger.info("File uploaded to cloud storage", backend=self.backend, key=storage_key)
                return storage_key
            except ClientError as e:
                logger.error("Cloud storage upload failed, falling back to local", error=str(e))

        # Local filesystem fallback
        dest_path = self.local_dir / storage_key
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_bytes(file_bytes)
        logger.info("File uploaded to local storage", path=str(dest_path))
        return storage_key

    def generate_signed_url(
        self,
        storage_key: str,
        original_filename: Optional[str] = None,
        expires_in: int = 3600,
        for_download: bool = True,
    ) -> str:
        """
        Generate pre-signed expiring URL for direct secure download/streaming.
        """
        if self.backend in ("s3", "r2") and (settings.AWS_ACCESS_KEY_ID or settings.R2_ACCESS_KEY_ID):
            try:
                client = self._get_s3_client()
                bucket = self._get_bucket_name()
                params = {"Bucket": bucket, "Key": storage_key}
                if original_filename:
                    disposition = "attachment" if for_download else "inline"
                    params["ResponseContentDisposition"] = f'{disposition}; filename="{original_filename}"'

                signed_url = client.generate_presigned_url(
                    "get_object",
                    Params=params,
                    ExpiresIn=expires_in,
                )
                return signed_url
            except Exception as e:
                logger.error("Presigned URL generation failed", error=str(e))

        # Secure HMAC-signed local link
        expiry = int(time.time()) + expires_in
        sig_data = f"{storage_key}:{expiry}".encode()
        secret = (settings.SECRET_KEY or "edusaas_local_secret_key").encode()
        signature = hmac.new(secret, sig_data, sha256).hexdigest()
        disposition_param = "download" if for_download else "preview"
        return f"/api/v1/materials/files/stream?key={storage_key}&exp={expiry}&sig={signature}&mode={disposition_param}"

    def verify_signed_local_token(self, storage_key: str, expiry: int, signature: str) -> bool:
        if time.time() > expiry:
            return False
        sig_data = f"{storage_key}:{expiry}".encode()
        secret = (settings.SECRET_KEY or "edusaas_local_secret_key").encode()
        expected = hmac.new(secret, sig_data, sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    def read_local_file(self, storage_key: str) -> Tuple[bytes, str]:
        path = self.local_dir / storage_key
        if not path.exists():
            raise BadRequestException("Requested file not found on storage server.")
        ext = path.suffix.lower()
        mime_map = {
            ".pdf": "application/pdf",
            ".doc": "application/msword",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".ppt": "application/vnd.ms-powerpoint",
            ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".mp4": "video/mp4",
            ".zip": "application/zip",
        }
        return path.read_bytes(), mime_map.get(ext, "application/octet-stream")

    def delete_file(self, storage_key: str) -> bool:
        if self.backend in ("s3", "r2") and (settings.AWS_ACCESS_KEY_ID or settings.R2_ACCESS_KEY_ID):
            try:
                client = self._get_s3_client()
                bucket = self._get_bucket_name()
                client.delete_object(Bucket=bucket, Key=storage_key)
                return True
            except Exception as e:
                logger.error("Failed to delete cloud object", error=str(e), key=storage_key)

        path = self.local_dir / storage_key
        if path.exists():
            path.unlink()
            return True
        return False


storage_service = StorageService()
