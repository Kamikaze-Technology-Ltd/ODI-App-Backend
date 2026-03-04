from django.db import models
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from uuid import uuid4

# Create your models here.
def generate_id():
    return uuid4().hex

class UserManager(BaseUserManager):
    def create_user(self, phone_number, password=None, **kwargs):
        if not phone_number:
            raise ValueError("The phone number must be provided")

        if not password:
            raise ValueError("The password must be provided")

        user = self.model(phone_number=phone_number, **kwargs)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, password=None, **kwargs):
        kwargs.setdefault('is_staff', True)
        kwargs.setdefault('is_superuser', True)

        return self.create_user(phone_number, password, **kwargs)

# Create your models here.
class User(AbstractUser):
    USERNAME_FIELD = 'phone_number'
    username = None
    id = models.CharField(max_length=255, primary_key= True, default = generate_id, null=False)
    phone_number = models.CharField(max_length=20, unique=True, null=False)
    driver_id = models.CharField(max_length=10, unique=True, null=False)
    REQUIRED_FIELDS = []
    objects = UserManager()