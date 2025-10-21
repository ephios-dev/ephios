from django.db import models
from django.db.models import (
    CharField,
    DateField,
    DateTimeField,
    ForeignKey,
)
from django.utils.translation import gettext_lazy as _
from ephios.core.models import UserProfile, Qualification

class QualificationRequest(models.Model):
    user = ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name='qualification_requests',
        verbose_name=_("User"),
    )
    qualification = ForeignKey(
        Qualification,
        on_delete=models.CASCADE,
        related_name='qualification_request',
        verbose_name=_("Qualification"),
    )
    qualification_date = DateField(
        null=False,
        blank=False,
        verbose_name=_("Qualification Date"),
    )
    expiration_date = DateField(
        null=True,
        blank=True,
        verbose_name=_("Expiration Date"),
    )
    created_at = DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created At"),
    )
    user_comment = CharField(
        null=True,
        blank=True,
        verbose_name=_("User Comment"),
    )
    status = CharField(
        max_length=20,
        choices=[
            ('pending', _("Pending")),
            ('approved', _("Approved")),
            ('rejected', _("Rejected")),
        ],
        default='pending',
        verbose_name=_("Status"),
    )
    reason = CharField(
        null=True,
        blank=True,
        verbose_name=_("Reason"),
    )
    #image_data = models.BinaryField(null=True, blank=True)
    #image_content_type = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return _(
            "%(user)s requested %(qualification)s on %(created)s (Status: %(status)s)"
        ) % {
            "user": self.user,
            "qualification": self.qualification,
            "created": self.created_at.strftime("%d.%m.%Y %H:%M"),
            "status": self.status,  # zeigt die übersetzte Status-Option
        }