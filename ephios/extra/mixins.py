import functools
from typing import Collection

from django.contrib.auth.mixins import AccessMixin, PermissionRequiredMixin
from django.shortcuts import redirect
from django.urls import resolve


class CustomPermissionRequiredMixin(PermissionRequiredMixin):
    """
    We modify Django's Mixin to support object permissions:
    * Logged in users without permission get 403
    * not logged in users get redirected to login

    Set accept_object_perms to False to disable
    object permissions (e.g. on create views).
    """

    accept_global_perms = True
    accept_object_perms = True

    def get_permission_object(self):
        if hasattr(self, "permission_object"):
            return self.permission_object
        if hasattr(self, "get_object") and (obj := self.get_object()) is not None:
            return obj
        return getattr(self, "object", None)

    def has_permission(self):
        user = self.request.user
        perms = self.get_permission_required()
        if self.accept_global_perms and all(user.has_perm(perm) for perm in perms):
            return True
        if not self.accept_object_perms or (obj := self.get_permission_object()) is None:
            return False
        return all(user.has_perm(perm, obj) for perm in perms)


class StaffRequiredMixin(AccessMixin):
    """Verify that the current user is staff."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)


class CanonicalSlugDetailMixin:
    """
    A mixin that enforces a canonical slug in the url.
    If a urlpattern takes a object's pk and slug as arguments and the slug url
    argument does not equal the object's canonical slug, this mixin will
    redirect to the url containing the canonical slug.

    Taken from django-braces, licenced under BSD Licence 2.0:
    Copyright (c) Brack3t and individual contributors.
    All rights reserved.

    Redistribution and use in source and binary forms, with or without modification,
    are permitted provided that the following conditions are met:

        1. Redistributions of source code must retain the above copyright notice,
           this list of conditions and the following disclaimer.

        2. Redistributions in binary form must reproduce the above copyright
           notice, this list of conditions and the following disclaimer in the
           documentation and/or other materials provided with the distribution.

        3. Neither the name of Brack3t nor the names of its contributors may be used
           to endorse or promote products derived from this software without
           specific prior written permission.

    THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
    ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
    WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
    DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
    ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
    (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
    LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
    ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
    (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
    SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
    """

    def dispatch(self, request, *args, **kwargs):
        # Set up since we need to super() later instead of earlier.
        self.request = request
        self.args = args
        self.kwargs = kwargs

        # Get the current object, url slug, and
        # urlpattern name (namespace aware).
        obj = self.get_object()
        slug = self.kwargs.get(self.slug_url_kwarg, None)
        match = resolve(request.path_info)
        url_parts = match.namespaces
        url_parts.append(match.url_name)
        current_urlpattern = ":".join(url_parts)

        # Figure out what the slug is supposed to be.
        if hasattr(obj, "get_canonical_slug"):
            canonical_slug = obj.get_canonical_slug()
        else:
            canonical_slug = self.get_canonical_slug()

        # If there's a discrepancy between the slug in the url and the
        # canonical slug, redirect to the canonical slug.
        if canonical_slug != slug:
            params = {
                self.pk_url_kwarg: obj.pk,
                self.slug_url_kwarg: canonical_slug,
                "permanent": True,
            }
            return redirect(current_urlpattern, **params)

        return super().dispatch(request, *args, **kwargs)

    def get_canonical_slug(self):
        """
        Override this method to customize what slug should be considered
        canonical.
        Alternatively, define the get_canonical_slug method on this view's
        object class. In that case, this method will never be called.
        """
        return self.get_object().slug


class PluginFormMixin:
    @functools.cached_property
    def plugin_forms(self):
        forms = []
        for __, resp in self.get_plugin_forms():
            forms.extend(resp)
        return forms

    def get_context_data(self, **kwargs):
        kwargs["plugin_forms"] = self.plugin_forms
        return super().get_context_data(**kwargs)

    def is_valid(self, form):
        return form.is_valid() and all(plugin_form.is_valid() for plugin_form in self.plugin_forms)

    def form_valid(self, form):
        response = super().form_valid(form)
        self.save_plugin_forms()
        return response

    def save_plugin_forms(self):
        for plugin_form in self.plugin_forms:
            plugin_form.save()

    def get_plugin_forms(self) -> Collection["BasePluginFormMixin"]:
        raise NotImplementedError
