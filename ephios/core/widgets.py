from django.forms import Widget
from django_select2.forms import ModelSelect2MultipleWidget, ModelSelect2Widget

from ephios.core.models import UserProfile


class UserProfileWidget(ModelSelect2Widget):
    search_fields = ["email__icontains", "display_name__icontains"]

    def label_from_instance(self, obj):
        return obj.get_full_name()


class MultiUserProfileWidget(ModelSelect2MultipleWidget):
    model = UserProfile

    search_fields = ["email__icontains", "display_name__icontains"]

    def label_from_instance(self, obj):
        return obj.get_full_name()


class PreviousCommentWidget(Widget):
    template_name = "core/widgets/previous_comments.html"

    def __init__(self, *args, **kwargs):
        self.comments = kwargs.pop("comments")
        super().__init__(*args, **kwargs)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["comments"] = self.comments
        return context
