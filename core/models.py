from django.db import models


class Location(models.Model):
    """Shared location for tickets (optional) and device assignment (FR-12, FR-29)."""
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    class Meta:
        db_table = 'core_location'

    def __str__(self):
        return self.name
