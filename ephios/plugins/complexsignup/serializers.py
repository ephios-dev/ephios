import uuid

from rest_framework import serializers

from ephios.core.models import Qualification
from ephios.plugins.complexsignup.models import (
    BlockComposition,
    BlockQualificationRequirement,
    BuildingBlock,
    Position,
)


class BulkUpdateListSerializerMixin:
    def update(self, instance, validated_data):
        # Maps for id->instance and id->data item.
        object_mapping = {object.id: object for object in instance}
        create_ids = iter(range(-1, -len(validated_data) - 1, -1))
        data_mapping = {item["id"] or next(create_ids): item for item in validated_data}

        # Perform creations and updates.
        ret = []
        for object_id, data in data_mapping.items():
            object = object_mapping.get(object_id, None)
            if object is None:
                ret.append(self.child.create(data))
            else:
                ret.append(self.child.update(object, data))

        # Perform deletions.
        for object_id, object in object_mapping.items():
            if self.should_delete(object, data_mapping):
                object.delete()
        return ret

    def should_delete(self, object, data_mapping):
        raise NotImplementedError()


class DeleteFlagBulkUpdateListSerializerMixin(BulkUpdateListSerializerMixin):
    def should_delete(self, object, data_mapping):
        return object.id in data_mapping and data_mapping[object.id].get("deleted", False)


class DeleteAbsentBulkUpdateListSerializerMixin(BulkUpdateListSerializerMixin):
    def should_delete(self, object, data_mapping):
        return object.id not in data_mapping


class DeletedFlagModelSerializer(serializers.ModelSerializer):
    deleted = serializers.BooleanField(default=False, write_only=True)

    def create(self, validated_data):
        validated_data.pop("deleted")
        return super().create(validated_data)


class BuildingBlockListSerializer(
    DeleteFlagBulkUpdateListSerializerMixin, serializers.ListSerializer
):
    pass


class PositionListSerializer(DeleteAbsentBulkUpdateListSerializerMixin, serializers.ListSerializer):
    pass


class QualificationRequirementListSerializer(
    DeleteAbsentBulkUpdateListSerializerMixin, serializers.ListSerializer
):
    pass


class QualificationSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False, read_only=False)

    class Meta:
        model = Qualification
        fields = ["id", "title", "abbreviation"]


class NestedQualificationsModelSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False, allow_null=True, read_only=False)
    qualifications = QualificationSerializer(many=True, required=False)

    def _set_qualifications(self, instance, qualification_data):
        instance.qualifications.set(
            Qualification.objects.filter(pk__in=[dict(q)["id"] for q in qualification_data])
        )

    def update(self, instance, validated_data):
        qualification_data = validated_data.pop("qualifications")
        instance = super().update(instance, validated_data)
        self._set_qualifications(instance, qualification_data)
        return instance

    def create(self, validated_data):
        qualification_data = validated_data.pop("qualifications")
        validated_data["block"] = self.context["block"]
        instance = super().create(validated_data)
        self._set_qualifications(instance, qualification_data)
        return instance


class PositionSerializer(NestedQualificationsModelSerializer):
    class Meta:
        model = Position
        fields = [
            "id",
            "label",
            "optional",
            "qualifications",
        ]
        list_serializer_class = PositionListSerializer


class BlockQualificationRequirementSerializer(NestedQualificationsModelSerializer):
    class Meta:
        model = BlockQualificationRequirement
        fields = [
            "id",
            "qualifications",
            "everyone",
            "at_least",
        ]
        list_serializer_class = QualificationRequirementListSerializer


class BlockCompositionSerializer(serializers.ModelSerializer):
    optional = serializers.BooleanField(required=True)
    sub_block = serializers.SlugRelatedField(
        slug_field="uuid", queryset=BuildingBlock.objects.all(), required=True
    )

    class Meta:
        model = BlockComposition
        fields = [
            "optional",
            "sub_block",
        ]


class BuildingBlockSerializer(DeletedFlagModelSerializer):
    id = serializers.IntegerField(required=False, allow_null=True, read_only=False)
    positions = PositionSerializer(many=True, required=False)
    qualification_requirements = BlockQualificationRequirementSerializer(many=True, required=False)
    sub_compositions = BlockCompositionSerializer(many=True, required=False)

    # explicit field to avoid unique check broken in nested serializers
    uuid = serializers.UUIDField(required=False, default=uuid.uuid4)

    def create_update_with_context(self, validated_data, instance_getter):
        positions_data = validated_data.pop("positions")
        qualification_requirements_data = validated_data.pop("qualification_requirements")

        instance = instance_getter()
        positions = PositionSerializer(
            instance=instance.positions.all(),
            data=positions_data,
            many=True,
            context={"block": instance},
        )
        positions.is_valid(raise_exception=True)
        positions.save()
        qualification_requirements = BlockQualificationRequirementSerializer(
            instance=instance.qualification_requirements.all(),
            data=qualification_requirements_data,
            many=True,
            context={"block": instance},
        )
        qualification_requirements.is_valid(raise_exception=True)
        qualification_requirements.save()
        return instance

    def create(self, validated_data):
        create = super().create
        return self.create_update_with_context(validated_data, lambda: create(validated_data))

    def update(self, instance, validated_data):
        update = super().update
        return self.create_update_with_context(
            validated_data, lambda: update(instance, validated_data)
        )

    class Meta:
        model = BuildingBlock
        fields = [
            "id",
            "uuid",
            "name",
            "block_type",
            "sub_compositions",
            "allow_more",
            "qualification_requirements",
            "positions",
            "deleted",
        ]
        list_serializer_class = BuildingBlockListSerializer
