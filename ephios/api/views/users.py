from oauth2_provider.contrib.rest_framework import IsAuthenticatedOrTokenHasScope
from rest_framework.generics import RetrieveAPIView
from rest_framework.serializers import ModelSerializer

from ephios.core.models import UserProfile


class UserProfileSerializer(ModelSerializer):
    class Meta:
        model = UserProfile
        fields = [
            "first_name",
            "last_name",
            "date_of_birth",
            "email",
        ]


class UserProfileMeView(RetrieveAPIView):
    serializer_class = UserProfileSerializer
    queryset = UserProfile.objects.all()
    permission_classes = [IsAuthenticatedOrTokenHasScope]
    required_scopes = ["ME_READ"]

    def get_object(self):
        return self.request.user
