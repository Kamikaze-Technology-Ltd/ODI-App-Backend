import cloudinary.uploader

def upload_image(file, folder="profiles", resource_type="auto"):
    result = cloudinary.uploader.upload(file, folder=folder, resource_type=resource_type)
    return result.get("secure_url")