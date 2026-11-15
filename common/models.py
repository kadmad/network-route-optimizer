"""Abstract base models shared by the domain apps."""

from django.db import models


class CreatedAtModel(models.Model):
    """Abstract model adding an immutable creation timestamp.

    ``created_at`` is set once by the database layer of Django (``auto_now_add``) in UTC.
    ``updated_at`` is intentionally omitted: no entity in this domain is mutable.
    """

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True
