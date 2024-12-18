from django.db import models
from django.utils.translation import gettext_lazy as _


class Page(models.Model):
    title = models.CharField(verbose_name=_("Title"), max_length=250)
    content = models.TextField(_("Content"), blank=True)
    slug = models.SlugField(
        _("URL slug"),
        help_text=_("The slug is used to generate the page's URL."),
        max_length=250,
        unique=True,
    )
    show_in_footer = models.BooleanField(_("Show in footer"), default=False)
    publicly_visible = models.BooleanField(_("Publicly visible"), default=False)

    def __str__(self):
        return str(self.title)

    class Meta:
        verbose_name = "Page"
        verbose_name_plural = "Pages"
