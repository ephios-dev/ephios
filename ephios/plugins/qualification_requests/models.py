from django.db import models
from django.utils.translation import gettext_lazy as _
from ephios.core.models import UserProfile, Qualification

class QualificationRequest(models.Model):
    user = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name='qualification_requests',
        verbose_name=_("User"),
    )
    qualification = models.ForeignKey(
        Qualification,
        on_delete=models.CASCADE,
        related_name='qualification_request',
        verbose_name=_("Qualification"),
    )
    qualification_date = models.DateField(
        null=False,
        blank=False,
        verbose_name=_("Qualification Date"),
    )
    expiration_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Expiration Date"),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created At"),
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', _("Pending")),
            ('approved', _("Approved")),
            ('rejected', _("Rejected")),
        ],
        default='pending',
        verbose_name=_("Status"),
    )
    #image_data = models.BinaryField(null=True, blank=True)
    #image_content_type = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f"{self.user} requested {self.qualification} on {self.created_at}"