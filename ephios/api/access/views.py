from django import forms
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import CreateView, TemplateView
from guardian.mixins import LoginRequiredMixin
from oauth2_provider import views as oauth2_views
from oauth2_provider.models import get_application_model
from oauth2_provider.scopes import get_scopes_backend

from ephios.api.models import AccessToken
from ephios.extra.mixins import StaffRequiredMixin
from ephios.extra.widgets import CustomSplitDateTimeWidget


class IgnoreApplicationOwnerMixin:
    def get_queryset(self):
        return get_application_model().objects.all()


class AllUserApplicationList(
    StaffRequiredMixin, IgnoreApplicationOwnerMixin, oauth2_views.ApplicationList
):
    pass


class ApplicationDetail(
    StaffRequiredMixin, IgnoreApplicationOwnerMixin, oauth2_views.ApplicationDetail
):
    pass


class ApplicationDelete(
    StaffRequiredMixin, IgnoreApplicationOwnerMixin, oauth2_views.ApplicationDelete
):
    success_url = reverse_lazy("api:settings-oauth-app-list")


class ApplicationUpdate(
    StaffRequiredMixin, IgnoreApplicationOwnerMixin, oauth2_views.ApplicationUpdate
):
    pass


class AccessTokensListView(oauth2_views.AuthorizedTokensListView):
    template_name = "api/access_token_list.html"

    context_object_name = "personal_access_tokens"

    def get_queryset(self):
        # personal API tokens
        qs = super().get_queryset().filter(user=self.request.user, application__id=None)
        return qs.order_by("-created")

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(object_list=object_list, **kwargs)
        context["oauth_access_tokens"] = AccessToken.objects.filter(
            user=self.request.user,
            application_id__isnull=False,
        )
        return context


class TokenScopesChoiceField(forms.MultipleChoiceField):
    def clean(self, value):
        scopes_list = super().clean(value)
        return " ".join(scopes_list)

    def to_python(self, value):
        # this should be the corresponding method to clean,
        # but it is not called/tested
        if isinstance(value, str):
            return value.split(" ")
        return value


class AccessTokenForm(forms.ModelForm):
    description = forms.CharField(
        label=_("Description"),
        widget=forms.TextInput(attrs={"placeholder": _("What is this token for?")}),
        required=True,
    )
    scope = TokenScopesChoiceField(
        label=_("Scope"),
        choices=[
            (scope, mark_safe(f"<code>{scope}</code>: {description}"))
            for scope, description in get_scopes_backend().get_all_scopes().items()
        ],
        widget=forms.CheckboxSelectMultiple,
        help_text=_("For security reasons, only select the scopes that are actually needed."),
    )
    expires = forms.SplitDateTimeField(
        label=_("expiration date"),
        widget=CustomSplitDateTimeWidget,
        required=False,
    )

    class Meta:
        model = AccessToken
        fields = ["description", "scope", "expires"]


def generate_key():
    return get_random_string(50)


class AccessTokenCreateView(LoginRequiredMixin, CreateView):
    model = AccessToken
    form_class = AccessTokenForm
    template_name = "api/access_token_form.html"

    def form_valid(self, form):
        """If the form is valid, save the associated model."""
        token = form.save(commit=False)
        token.user = self.request.user
        token.token = generate_key()
        token.save()
        return redirect("api:settings-access-token-reveal", pk=token.pk)


class AccessTokenRevealView(LoginRequiredMixin, TemplateView):
    template_name = "api/access_token_reveal.html"

    def get(self, request, *args, **kwargs):
        try:
            token = AccessToken.objects.get(pk=self.kwargs["pk"], user=self.request.user)
        except AccessToken.DoesNotExist:
            raise PermissionDenied
        if token.created < timezone.now() - timezone.timedelta(seconds=30):
            messages.error(request, _("Token is too old to be revealed."))
            return redirect("api:settings-access-token-list")
        context = self.get_context_data(token=token, **kwargs)
        return self.render_to_response(context)


class AccessTokenRevokeView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        # user can only revoke own tokens
        get_object_or_404(AccessToken, pk=request.POST["pk"], user=request.user).revoke_related()
        messages.success(request, _("Token was revoked."))
        return redirect("api:settings-access-token-list")
