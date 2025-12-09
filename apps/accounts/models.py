from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    A Custom extendable user model. This user model maps 1 - 1 with Profile models.
    """

    username = None
    email = models.EmailField(unique=True, db_index=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def __str__(self) -> str:
        return self.email
