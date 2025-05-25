from django.db import models
from django.utils.translation import gettext_lazy as _


class Question(models.Model):
    TYPE_TEXT = "text"
    TYPE_SINGLE_RADIO = "single_radio"
    TYPE_SINGLE_LIST = "single_list"
    TYPE_MULTIPLE = "multiple"
    TYPE_CHOICES = [
        (TYPE_TEXT, _("Text input")),
        (TYPE_SINGLE_RADIO, _("Single choice")),
        (TYPE_SINGLE_LIST, _("Single choice (list)")),
        (TYPE_MULTIPLE, _("Multiple choice")),
    ]

    name = models.CharField(
        max_length=50,
        verbose_name=_("Name"),
        help_text=_(
            "The name of the question is used to identify the question, for example when picking questions for a shift"
        ),
    )
    question_text = models.CharField(max_length=100, verbose_name=_("Question"))
    description = models.TextField(verbose_name=_("Description"), blank=True, null=True)
    required = models.BooleanField(
        verbose_name=_("Required"),
        help_text=_("Whether users must submit an answer to this question"),
    )
    type = models.CharField(
        max_length=20, verbose_name=_("Type"), choices=TYPE_CHOICES, default=TYPE_TEXT
    )
    choices = models.JSONField(default=list, verbose_name=_("Choices"))

    class Meta:
        verbose_name = _("Question")
        verbose_name_plural = _("Questions")

    def __str__(self):
        # pylint: disable=invalid-str-returned
        return self.name
