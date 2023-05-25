from django import forms
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import CreateView, TemplateView
from guardian.mixins import LoginRequiredMixin
from oauth2_provider import views as outh2_views
from oauth2_provider.models import get_application_model
from oauth2_provider.scopes import get_scopes_backend

from ephios.api.models import AccessToken
from ephios.extra.mixins import StaffRequiredMixin
from ephios.extra.widgets import CustomSplitDateTimeWidget


class AllUserApplicationList(StaffRequiredMixin, outh2_views.ApplicationList):
    def get_queryset(self):
        return get_application_model().objects.all()


class AccessTokensListView(outh2_views.AuthorizedTokensListView):
    template_name = "api/access_token_list.html"

    def get_queryset(self):
        qs = super().get_queryset().select_related("application").filter(user=self.request.user)
        if not self.request.GET.get("show_inactive"):
            qs = qs.filter(
                Q(expires__gt=timezone.now()) | Q(expires__isnull=True),
                revoked__isnull=True,
            )
        return qs.order_by("-created")


class TokenScopesChoiceField(forms.MultipleChoiceField):
    def clean(self, value):
        scopes_list = super().clean(value)
        return " ".join(scopes_list)

    def to_python(self, value):  # TODO is this correct?
        if isinstance(value, str):
            return value.split(" ")
        return value


class AccessTokenForm(forms.ModelForm):
    description = forms.CharField(
        widget=forms.Textarea(
            attrs={"placeholder": _("Describe where and for what this token is used"), "rows": 1}
        ),
        required=True,
    )
    scope = TokenScopesChoiceField(
        choices=[
            (scope, mark_safe(f"<code>{scope}</code>: {description}"))
            for scope, description in get_scopes_backend().get_all_scopes().items()
        ],
        widget=forms.CheckboxSelectMultiple,
        help_text=_("For security reasons, only select the scopes that are actually needed."),
    )
    expires = forms.SplitDateTimeField(
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
    success_message = _(
        "Event type was created. More settings for this event type can be managed below."
    )

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
