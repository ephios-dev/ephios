from rest_framework import serializers

from ephios.core.models import Qualification, QualificationCategory


class QualificationCategoryFixtureSerializer(serializers.ModelSerializer):
    uuid = serializers.UUIDField(label="UUID")

    class Meta:
        model = QualificationCategory
        fields = ["uuid", "title"]


class IncludedUuidsField(serializers.RelatedField):
    """This field converts a Qualification to its uuid, but keeps the UUID on deserialization."""

    def to_representation(self, value):
        return str(value.uuid)

    def to_internal_value(self, data):
        return data


class QualificationFixtureSerializer(serializers.ModelSerializer):
    uuid = serializers.UUIDField(label="UUID")
    includes = IncludedUuidsField(many=True, queryset=Qualification.objects.none())
    included_by = IncludedUuidsField(many=True, queryset=Qualification.objects.none())
    category = QualificationCategoryFixtureSerializer()

    class Meta:
        model = Qualification
        fields = [
            "uuid",
            "title",
            "abbreviation",
            "includes",
            "included_by",
            "category",
        ]
