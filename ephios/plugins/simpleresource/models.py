from django.db import models

from ephios.core.models import Shift


class ResourceCategory(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        # pylint: disable=invalid-str-returned
        return self.name


class Resource(models.Model):
    title = models.CharField(max_length=100)
    category = models.ForeignKey(ResourceCategory, on_delete=models.CASCADE)

    def __str__(self):
        # pylint: disable=invalid-str-returned
        return self.title


class ResourceAllocation(models.Model):
    shift = models.ForeignKey(Shift, on_delete=models.CASCADE)
    resources = models.ManyToManyField(Resource, blank=True)

    def __str__(self):
        return f"Resource allocation for {self.shift}"
