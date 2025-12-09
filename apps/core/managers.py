from django.db import models
from django.utils import timezone


class SoftDeleteQuerySet(models.QuerySet):
    def delete(self):
        """
        Soft delete: Mark rows as deleted instead of hard-deleting.
        """
        return super().update(deleted_at=timezone.now())

    def hard_delete(self):
        """
        Hard delete: Actually delete rows from the database.
        """
        return super().delete()

    def deleted(self):
        return self.filter(deleted_at__isnull=False)


class SoftDeleteManager(models.Manager):
    """
    Default manager that hides soft-deleted rows.
    """

    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).filter(deleted_at__isnull=True)