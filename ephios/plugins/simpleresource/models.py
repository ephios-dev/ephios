from django.db import models


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
