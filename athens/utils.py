import logging
import cloudinary.uploader
import random
import string
from uuid import uuid4

logger = logging.getLogger(__name__)


def upload_image(file, folder="profiles", resource_type="auto"):
    logger.info(f"[Cloudinary] Uploading file to folder='{folder}' | filename='{getattr(file, 'name', 'unknown')}'")
    try:
        result = cloudinary.uploader.upload(file, folder=folder, resource_type=resource_type)
        url = result.get("secure_url")
        if url:
            logger.info(f"[Cloudinary] Upload successful → {url}")
        else:
            logger.warning("[Cloudinary] Upload returned no URL. Check credentials or file type.")
        return url
    except Exception as e:
        logger.error(f"[Cloudinary] Upload FAILED: {str(e)}")
        raise


def generate_otp():
    return ''.join(random.choices(string.digits, k=6))


def generate_reset_token():
    return uuid4().hex
