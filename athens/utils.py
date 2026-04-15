import cloudinary.uploader
import random
import string
from uuid import uuid4

def upload_image(file, folder="profiles", resource_type="auto"):
    result = cloudinary.uploader.upload(file, folder=folder, resource_type=resource_type)
    return result.get("secure_url")

def generate_otp():
    return ''.join(random.choices(string.digits, k=6))

def generate_reset_token():
    return uuid4().hex