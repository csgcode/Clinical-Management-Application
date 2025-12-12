from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ObjectDoesNotExist
from django.db import models

from .managers import UserManager


class User(AbstractUser):
    """
    A Custom extendable user model. This user model maps 1 - 1 with Profile models.
    """

    username = None
    email = models.EmailField(unique=True, db_index=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def __str__(self) -> str:
        return self.email
    

    def _has_related(self, attr: str) -> bool:
        try:
            getattr(self, attr)
            return True
        except ObjectDoesNotExist:
            return False

    @property
    def has_clinician_profile(self) -> bool:
        return self._has_related("clinician_profile")

    @property
    def has_patient_profile(self) -> bool:
        return self._has_related("patient_profile")