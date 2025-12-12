from django.db import models
from django.utils import timezone

from .managers import SoftDeleteManager, IsActiveManager


class TimeStampedModel(models.Model):
    """
    Abstract base model that provides created_at / updated_at timestamps.
    """

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        abstract = True


class SoftDeleteModel(models.Model):
    """
    Abstract base model for soft deletion, using a nullable deleted_at field.
    """

    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    objects = SoftDeleteManager()

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at"])

    def hard_delete(self, using=None, keep_parents=False):
        super().delete(using=using, keep_parents=keep_parents)

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None


class IsActiveBaseModel(models.Model):
    """
    Abstract base model for is_active usage

    TODO Implement this base model.
    """

    is_active = models.BooleanField(
        default=True, help_text="Set to False to retire this object"
    )

    objects = IsActiveManager()

    class Meta:
        abstract = True
