from django_select2.forms import ModelSelect2Widget, ModelSelect2MultipleWidget

from user_management.models import UserProfile


class UserProfileWidget(ModelSelect2Widget):
    search_fields = ["email__icontains", "first_name__icontains", "last_name__icontains"]

    def label_from_instance(self, obj):
        return obj.get_full_name()


class MultiUserProfileWidget(ModelSelect2MultipleWidget):
    model = UserProfile

    search_fields = ["email__icontains", "first_name__icontains", "last_name__icontains"]

    def label_from_instance(self, obj):
        return obj.get_full_name()
