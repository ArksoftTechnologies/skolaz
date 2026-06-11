"""
Skolaz v2.0 — Storage Service
Pluggable storage: local filesystem (dev) → AWS S3 / Cloudflare R2 (prod)
"""
import os
import uuid
from flask import current_app
from werkzeug.utils import secure_filename


def _backend() -> str:
    return current_app.config.get("STORAGE_BACKEND", "local").lower()


# ── Upload ────────────────────────────────────────────────────────────────────

def upload_file(file_obj, folder: str = "uploads", filename: str = None) -> dict:
    """
    Upload a file to the configured backend.
    Returns: { url, filename, size_bytes, mime_type }
    """
    original_filename = secure_filename(file_obj.filename)
    ext = original_filename.rsplit(".", 1)[-1].lower() if "." in original_filename else ""
    safe_name = filename or f"{uuid.uuid4().hex}.{ext}"

    if _backend() == "s3":
        return _upload_s3(file_obj, folder, safe_name)
    elif _backend() == "r2":
        return _upload_r2(file_obj, folder, safe_name)
    else:
        return _upload_local(file_obj, folder, safe_name)


def delete_file(file_url: str) -> bool:
    """Delete a file from the configured backend."""
    try:
        if _backend() in ("s3", "r2"):
            return _delete_s3_or_r2(file_url)
        else:
            return _delete_local(file_url)
    except Exception:
        return False


# ── Local Storage ─────────────────────────────────────────────────────────────

def _upload_local(file_obj, folder: str, filename: str) -> dict:
    upload_root = current_app.config.get("UPLOAD_FOLDER", "uploads")
    dest_dir = os.path.join(upload_root, folder)
    os.makedirs(dest_dir, exist_ok=True)
    dest_path = os.path.join(dest_dir, filename)
    file_obj.save(dest_path)
    size = os.path.getsize(dest_path)
    url = f"/uploads/{folder}/{filename}"
    return {
        "url": url,
        "filename": filename,
        "size_bytes": size,
        "mime_type": file_obj.mimetype,
    }


def _delete_local(file_url: str) -> bool:
    upload_root = current_app.config.get("UPLOAD_FOLDER", "uploads")
    # file_url like /uploads/documents/abc.pdf → strip leading /
    rel = file_url.lstrip("/")
    full_path = os.path.join(os.getcwd(), rel)
    if os.path.exists(full_path):
        os.remove(full_path)
        return True
    return False


# ── AWS S3 ────────────────────────────────────────────────────────────────────

def _get_s3_client():
    import boto3
    cfg = current_app.config
    return boto3.client(
        "s3",
        aws_access_key_id=cfg.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=cfg.get("AWS_SECRET_ACCESS_KEY"),
        region_name=cfg.get("AWS_S3_REGION", "us-east-1"),
    )


def _upload_s3(file_obj, folder: str, filename: str) -> dict:
    cfg = current_app.config
    client = _get_s3_client()
    bucket = cfg.get("AWS_S3_BUCKET")
    key = f"{folder}/{filename}"
    file_obj.seek(0)
    client.upload_fileobj(
        file_obj, bucket, key,
        ExtraArgs={"ContentType": file_obj.mimetype, "ACL": "public-read"},
    )
    url = f"https://{bucket}.s3.{cfg.get('AWS_S3_REGION', 'us-east-1')}.amazonaws.com/{key}"
    return {"url": url, "filename": filename, "size_bytes": None, "mime_type": file_obj.mimetype}


# ── Cloudflare R2 ─────────────────────────────────────────────────────────────

def _upload_r2(file_obj, folder: str, filename: str) -> dict:
    import boto3
    cfg = current_app.config
    client = boto3.client(
        "s3",
        endpoint_url=cfg.get("R2_ENDPOINT_URL"),
        aws_access_key_id=cfg.get("R2_ACCESS_KEY_ID"),
        aws_secret_access_key=cfg.get("R2_SECRET_ACCESS_KEY"),
    )
    bucket = cfg.get("R2_BUCKET")
    key = f"{folder}/{filename}"
    file_obj.seek(0)
    client.upload_fileobj(file_obj, bucket, key,
                          ExtraArgs={"ContentType": file_obj.mimetype})
    url = f"{cfg.get('R2_ENDPOINT_URL')}/{bucket}/{key}"
    return {"url": url, "filename": filename, "size_bytes": None, "mime_type": file_obj.mimetype}


def _delete_s3_or_r2(file_url: str) -> bool:
    # Simplified — extract key from URL
    cfg = current_app.config
    if _backend() == "s3":
        client = _get_s3_client()
        bucket = cfg.get("AWS_S3_BUCKET")
    else:
        import boto3
        client = boto3.client(
            "s3",
            endpoint_url=cfg.get("R2_ENDPOINT_URL"),
            aws_access_key_id=cfg.get("R2_ACCESS_KEY_ID"),
            aws_secret_access_key=cfg.get("R2_SECRET_ACCESS_KEY"),
        )
        bucket = cfg.get("R2_BUCKET")
    key = file_url.split(f"{bucket}/")[-1]
    client.delete_object(Bucket=bucket, Key=key)
    return True
