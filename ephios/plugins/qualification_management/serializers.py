from rest_framework import serializers

from ephios.core.models import Qualification, QualificationCategory


class QualificationCategoryFixtureSerializer(serializers.ModelSerializer):
    class Meta:
        model = QualificationCategory
        fields = ["uuid", "title"]


class QualificationFixtureSerializer(serializers.ModelSerializer):
    includes = serializers.SlugRelatedField(many=True, read_only=True, slug_field="uuid")
    included_by = serializers.SlugRelatedField(many=True, read_only=True, slug_field="uuid")
    category = QualificationCategoryFixtureSerializer(read_only=True)

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
