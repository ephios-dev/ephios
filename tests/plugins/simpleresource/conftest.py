import pytest

from ephios.plugins.simpleresource.models import Resource, ResourceCategory


@pytest.fixture
def resources():
    category = ResourceCategory.objects.create(name="Test Category")
    resource1 = Resource.objects.create(title="Test Resource 1", category=category)
    resource2 = Resource.objects.create(title="Test Resource 2", category=category)
    return resource1, resource2
