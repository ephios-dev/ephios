from django.db.models import Q
from django.utils import timezone
from oauth2_provider.contrib.rest_framework import IsAuthenticatedOrTokenHasScope
from rest_framework.exceptions import PermissionDenied
from rest_framework.fields import SerializerMethodField
from rest_framework.generics import RetrieveAPIView
from rest_framework.relations import SlugRelatedField
from rest_framework.serializers import ModelSerializer

from ephios.core.models import Qualification, UserProfile
from ephios.core.services.qualification import collect_all_included_qualifications


class QualificationSerializer(ModelSerializer):
    category = SlugRelatedField(slug_field="uuid", read_only=True)
    includes = SerializerMethodField()

    class Meta:
        model = Qualification
        fields = [
            "uuid",
            "title",
            "abbreviation",
            "category",
            "includes",
        ]

    def get_includes(self, obj):
        return [q.uuid for q in collect_all_included_qualifications(obj.includes.all())]


class UserProfileSerializer(ModelSerializer):
    qualifications = SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = [
            "display_name",
            "date_of_birth",
            "email",
            "qualifications",
        ]

    def get_qualifications(self, obj):
        return QualificationSerializer(
            Qualification.objects.filter(
                Q(grants__user=obj)
                & (Q(grants__expires__gte=timezone.now()) | Q(grants__expires__isnull=True))
            ),
            many=True,
        ).data


class UserProfileMeView(RetrieveAPIView):
    serializer_class = UserProfileSerializer
    queryset = UserProfile.objects.all()
    permission_classes = [IsAuthenticatedOrTokenHasScope]
    required_scopes = ["ME_READ"]

    def get_object(self):
        if self.request.user is None:
            raise PermissionDenied()
        return self.request.user
