from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import (
    Model,
    CharField,
    TextField,
    ForeignKey,
    IntegerField,
    ManyToManyField,
    DateTimeField,
    BooleanField,
    Q,
)

from user_management.models import Qualification, UserProfile


class ResourcePosition(Model):
    title = CharField(max_length=254)
    amount = IntegerField()
    medical_qualification = IntegerField(
        choices=UserProfile.QUALIFICATION_MEDICAL_OPTIONS
    )
    qualification = ManyToManyField(Qualification, blank=True)

    def __str__(self):
        return self.title


class Resource(Model):
    title = CharField(max_length=254)
    positions = ManyToManyField(ResourcePosition)

    def __str__(self):
        return self.title


class Service(Model):
    title = CharField(max_length=254)
    description = TextField(blank=True, null=True)
    location = CharField(max_length=254)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("service_management:service_detail", args=[str(self.id)])


class Shift(Model):
    service = ForeignKey(Service, on_delete=models.CASCADE)
    start_time = DateTimeField()
    end_time = DateTimeField()
    resources = ManyToManyField(Resource)
    minors_allowed = BooleanField()

    def __str__(self):
        return f"{self.service.title} ({self.start_time}-{self.end_time})"


class Participation(Model):
    user = ForeignKey(get_user_model(), on_delete=models.CASCADE)
    shift = ForeignKey(Shift, on_delete=models.CASCADE)
    resource_position = ForeignKey(
        ResourcePosition, on_delete=models.CASCADE, blank=True
    )
    accepted = BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "shift"], name="unique_shift_participation"
            )
        ]

    def __str__(self):
        return f"{self.user.get_full_name()} @ {self.shift}"
