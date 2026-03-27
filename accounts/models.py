from django.contrib.auth.models import AbstractUser
from django.db import models

from .rbac import user_is_administrator, user_is_standard_user


class Role(models.Model):
    """Role for RBAC: Standard User, Administrator."""
    name = models.CharField(max_length=50, unique=True)

    class Meta:
        db_table = 'core_role'

    def __str__(self):
        return self.name


class User(AbstractUser):
    """Custom user with role FK. Email used for login (FR-1, FR-5)."""
    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='users',
    )

    class Meta:
        db_table = 'accounts_user'

    def __str__(self):
        return self.email or self.username

    @property
    def is_administrator(self):
        return user_is_administrator(self)

    @property
    def is_standard_user(self):
        return user_is_standard_user(self)
