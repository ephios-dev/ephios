from django.db import models

from ephios.core.models import Shift


class ResourceCategory(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name


class Resource(models.Model):
    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=100)
    category = models.ForeignKey(ResourceCategory, on_delete=models.CASCADE)

    def __str__(self):
        return self.title


class ResourceAllocation(models.Model):
    shift = models.ForeignKey(Shift, on_delete=models.CASCADE)
    resources = models.ManyToManyField(Resource)

    def __str__(self):
        return f"Resource allocation for {self.shift}"
