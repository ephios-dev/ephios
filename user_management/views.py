from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.models import Group
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.views.generic import DetailView, ListView, UpdateView, CreateView, DeleteView
from guardian.shortcuts import get_objects_for_group

from jep.settings import SITE_URL
from user_management.forms import GroupForm, UserProfileForm
from django.utils.translation import gettext as _

from user_management.models import UserProfile


class ProfileView(LoginRequiredMixin, DetailView):
    def get_object(self, queryset=None):
        return self.request.user


class UserProfileListView(PermissionRequiredMixin, ListView):
    model = UserProfile
    permission_required = "user_management.view_userprofile"

    def get_queryset(self):
        return UserProfile.objects.all()


class UserProfileCreateView(PermissionRequiredMixin, CreateView):
    template_name = "user_management/userprofile_form.html"
    permission_required = "user_management.add_userprofile"
    model = UserProfile
    form_class = UserProfileForm

    def get_success_url(self):
        messages.success(self.request, _("User added successfully."))
        return reverse("user_management:user_list")

    def form_valid(self, form):
        response = super().form_valid(form)
        userprofile = self.object
        self.send_mail(userprofile)
        return response

    def send_mail(self, userprofile):
        messages = []
        subject = _("Welcome to JEP!")
        uid = urlsafe_base64_encode(force_bytes(userprofile.id))
        token = default_token_generator.make_token(userprofile)
        reset_link = reverse("password_reset_confirm", kwargs={"uidb64": uid, "token": token})
        text_content = _(
            "You're receiving this email because a new account has been created for you at JEP.\n"
            "Please go to the following page and choose a password: {url}{reset_link}\n"
            "Your username is your email address: {email}\n"
            "Thanks for using our site!"
        ).format(url=SITE_URL, reset_link=reset_link, email=userprofile.email)

        html_content = render_to_string(
            "registration/password_reset_email.html",
            {"uid": uid, "token": token, "site_url": SITE_URL},
        )
        message = EmailMultiAlternatives(to=[userprofile.email], subject=subject, body=text_content)
        message.attach_alternative(html_content, "text/html")
        messages.append(message)

        mail.get_connection().send_messages(messages)


class GroupListView(PermissionRequiredMixin, ListView):
    model = Group
    permission_required = "auth.view_group"
    template_name = "user_management/group_list.html"


class GroupCreateView(PermissionRequiredMixin, CreateView):
    model = Group
    permission_required = "auth.add_group"
    template_name = "user_management/group_form.html"
    form_class = GroupForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["initial"] = {
            "users": UserProfile.objects.none(),
            "can_add_event": False,
            "publish_event_for_group": Group.objects.none(),
        }
        return kwargs

    def get_success_url(self):
        messages.success(self.request, _("Group created successfully."))
        return reverse("user_management:group_list")


class GroupUpdateView(PermissionRequiredMixin, UpdateView):
    model = Group
    permission_required = "auth.change_group"
    template_name = "user_management/group_form.html"
    form_class = GroupForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["initial"] = {
            "users": self.object.user_set.all(),
            "can_view_past_event": self.object.permissions.filter(
                codename="view_past_event"
            ).exists(),
            "can_add_event": self.object.permissions.filter(codename="add_event").exists(),
            "publish_event_for_group": get_objects_for_group(
                self.object, "publish_event_for_group", klass=Group
            ),
        }
        return kwargs

    def get_success_url(self):
        return reverse("user_management:group_list")


class GroupDeleteView(PermissionRequiredMixin, DeleteView):
    model = Group
    permission_required = "auth.delete_group"
    template_name = "user_management/group_confirm_delete.html"

    def get_success_url(self):
        return reverse("user_management:group_list")
