import uuid

from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers

from ephios.core.models import Qualification
from ephios.extra.graphs import DirectedGraph
from ephios.plugins.complexsignup.models import (
    BlockComposition,
    BlockQualificationRequirement,
    BuildingBlock,
    BuildingBlockType,
    Position,
)


class NestedSlugRelatedField(serializers.SlugRelatedField):
    """
    This is a workaround for the native SlugRelatedField not accepting
    model objects as input. With this we can feed validated data into
    nested serializers again.
    If the object does not exist, we keep the original value and let
    custom serializers handle it.
    """

    def to_internal_value(self, data):
        queryset = self.get_queryset()
        if isinstance(data, queryset.model):
            return data
        try:
            return queryset.get(**{self.slug_field: data})
        except ObjectDoesNotExist:
            return data  # let custom serializers handle it
        except (TypeError, ValueError):
            self.fail("invalid")
        return super().to_internal_value(data)


class BulkUpdateListSerializer(serializers.ListSerializer):
    identification_field = "id"

    def update(self, instance, validated_data):
        # Maps for id->instance and id->data item.
        object_mapping = {getattr(object, self.identification_field): object for object in instance}
        create_ids = iter(range(-1, -len(validated_data) - 1, -1))
        data_mapping = {
            item[self.identification_field] or next(create_ids): item for item in validated_data
        }

        # Perform creations and updates.
        ret = []
        for object_id, data in data_mapping.items():
            obj = object_mapping.get(object_id, None)
            if obj is None:
                obj = self.child.create(data.copy())
            else:
                obj = self.child.update(obj, data.copy())
            object_mapping[object_id] = obj  # update mapping for use in deletion later
            ret.append(obj)

        for obj in ret:
            if hasattr(obj, "save_m2m"):
                # you can defer validating/saving relationships on the serializer
                # by putting into this optional method
                obj.save_m2m()

        # Perform deletions.
        for object_id, obj in object_mapping.items():
            if self.should_delete(object_id, data_mapping):
                obj.delete()
        return ret

    def should_delete(self, object_id, data_mapping):
        raise NotImplementedError()


class DeleteFlagBulkUpdateListSerializer(BulkUpdateListSerializer):
    def should_delete(self, object_id, data_mapping):
        return object_id in data_mapping and data_mapping[object_id].get("deleted", False)


class DeleteAbsentBulkUpdateListSerializer(BulkUpdateListSerializer):
    def should_delete(self, object_id, data_mapping):
        return object_id not in data_mapping


class DeletedFlagModelSerializer(serializers.ModelSerializer):
    deleted = serializers.BooleanField(default=False, write_only=True)

    def create(self, validated_data):
        validated_data.pop("deleted")
        return super().create(validated_data)


class NestedQualificationsObjectSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=True, allow_null=True, read_only=False)
    qualifications = NestedSlugRelatedField(
        slug_field="id",
        queryset=Qualification.objects.all(),
        many=True,
    )

    def create(self, validated_data):
        validated_data["block"] = self.context["block"]
        return super().create(validated_data)


class PositionSerializer(NestedQualificationsObjectSerializer):
    class Meta:
        model = Position
        fields = [
            "id",
            "label",
            "optional",
            "qualifications",
        ]
        list_serializer_class = DeleteAbsentBulkUpdateListSerializer


class BlockQualificationRequirementSerializer(NestedQualificationsObjectSerializer):
    class Meta:
        model = BlockQualificationRequirement
        fields = [
            "id",
            "qualifications",
            "everyone",
            "at_least",
        ]
        list_serializer_class = DeleteAbsentBulkUpdateListSerializer


class BlockCompositionSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=True, allow_null=True, read_only=False)
    optional = serializers.BooleanField(required=True)
    label = serializers.CharField(required=True, allow_blank=True)
    sub_block = NestedSlugRelatedField(slug_field="uuid", queryset=BuildingBlock.objects.all())

    class Meta:
        model = BlockComposition
        fields = [
            "id",
            "label",
            "optional",
            "sub_block",
        ]
        list_serializer_class = DeleteAbsentBulkUpdateListSerializer

    def create(self, validated_data):
        validated_data["composite_block"] = self.context["block"]
        return super().create(validated_data)


class BuildingBlockListSerializer(DeleteFlagBulkUpdateListSerializer):
    identification_field = "uuid"

    def validate(self, attrs):
        # validate that there are no circles
        graph = DirectedGraph()
        for block in attrs:
            graph.add(
                str(block["uuid"]),
                [str(composition["sub_block"]) for composition in block["sub_compositions"]],
            )
        if not graph.is_acyclic():
            raise serializers.ValidationError(
                "Sub compositions must be free of cycles.", code="invalid"
            )
        return attrs


class BuildingBlockSerializer(DeletedFlagModelSerializer):
    id = serializers.IntegerField(required=False, read_only=True)
    uuid = serializers.UUIDField(required=False, default=uuid.uuid4)
    positions = PositionSerializer(many=True, required=False)
    qualification_requirements = BlockQualificationRequirementSerializer(many=True, required=False)
    sub_compositions = BlockCompositionSerializer(many=True, required=False)
    name = serializers.CharField(required=True, allow_blank=True)

    def create_update_with_context(self, validated_data, instance_getter):
        positions_data = validated_data.pop("positions")
        qualification_requirements_data = validated_data.pop("qualification_requirements")
        sub_compositions_data = validated_data.pop("sub_compositions")

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

        sub_compositions = BlockCompositionSerializer(
            instance=instance.sub_compositions.all(),
            data=sub_compositions_data,
            many=True,
            context={"block": instance},
        )

        def save_m2m():
            # because we would error if the sub_block doesn't exist in the database yet
            # we defer saving the sub compositions to after the whole list was saved
            sub_compositions.is_valid(raise_exception=True)
            sub_compositions.save()

        instance.save_m2m = save_m2m
        return instance

    def create(self, validated_data):
        create = super().create
        return self.create_update_with_context(validated_data, lambda: create(validated_data))

    def update(self, instance, validated_data):
        update = super().update
        return self.create_update_with_context(
            validated_data, lambda: update(instance, validated_data)
        )

    def validate(self, attrs):
        if attrs.get("block_type") == BuildingBlockType.COMPOSITE.value:
            if attrs.get("positions"):
                raise serializers.ValidationError(
                    "Composite blocks cannot have positions", code="invalid"
                )
        if attrs.get("block_type") == BuildingBlockType.ATOMIC.value:
            if attrs.get("sub_compositions"):
                raise serializers.ValidationError(
                    "Position blocks cannot have sub compositions", code="invalid"
                )
        if attrs.get("deleted") is False:
            if attrs.get("name") == "":
                raise serializers.ValidationError("Name cannot be blank.", code="invalid")
        return attrs

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
