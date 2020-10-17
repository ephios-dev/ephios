from django.db import models


class Page(models.Model):
    title = models.CharField(max_length=250)
    content = models.TextField(blank=True)
    slug = models.SlugField(max_length=250, unique=True)
    show_in_footer = models.BooleanField(default=False)
    publicly_visible = models.BooleanField(default=False)

    def __str__(self):
        return str(self.title)
