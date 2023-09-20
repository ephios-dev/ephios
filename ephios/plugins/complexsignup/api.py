from oauth2_provider.contrib.rest_framework import IsAuthenticatedOrTokenHasScope
from rest_framework import viewsets

from ephios.plugins.complexsignup.models import BuildingBlock
from ephios.plugins.complexsignup.serializers import BuildingBlockSerializer


class BuildingBlockViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = BuildingBlockSerializer
    permission_classes = [IsAuthenticatedOrTokenHasScope]
    required_scopes = ["PUBLIC_READ"]
    queryset = BuildingBlock.objects.all()
