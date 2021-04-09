import collections.abc
import json

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.db.models import QuerySet
from django.utils import dateparse
from django.utils.functional import SimpleLazyObject

# pylint: disable=protected-access


class LogJSONEncoder(DjangoJSONEncoder):
    """
    Encoder designed to handle querysets and model instances while falling back to their string representation in the corresponding Decoder.
    """

    def default(self, o):
        queryset_like = SimpleLazyObject(
            lambda: isinstance(o, collections.abc.Collection)
            and all(isinstance(elem, models.Model) for elem in o)
            and len({type(elem) for elem in o}) == 1
        )
        if isinstance(o, QuerySet) or queryset_like:
            pks, strs = [], []
            for instance in o:
                pks.append(instance.pk)
                strs.append(str(instance))
            return {
                "__model__": "__queryset__",
                "pks": pks,
                "strs": strs,
                "contenttype_id": ContentType.objects.get_for_model(
                    getattr(o, "model", None) or type(next(iter(o)))
                ).id,
            }
        if o == set():
            return []
        if isinstance(o, models.Model):
            return {
                "__model__": "__instance__",
                "pk": o.pk,
                "str": str(o),
                "contenttype_id": ContentType.objects.get_for_model(o).id,
            }
        return super().default(o)


class LogJSONDecoder(json.JSONDecoder):
    """
    Decoder designed to handle querysets and model instances while falling back to their string representation from the corresponding Encoder.
    """

    def __init__(self, *args, **kargs):
        super().__init__(*args, object_hook=self.custom_hook, **kargs)

    def custom_hook(self, d):
        if d.get("__model__") == "__queryset__":
            Model = ContentType.objects.get_for_id(d["contenttype_id"]).model_class()
            objects = {obj.pk: obj for obj in Model._base_manager.filter(pk__in=d["pks"])}
            return [objects.get(pk, s) for pk, s in zip(d["pks"], d["strs"])]
        if d.get("__model__") == "__instance__":
            try:
                return ContentType.objects.get_for_id(d["contenttype_id"]).get_object_for_this_type(
                    pk=d["pk"]
                )
            except ObjectDoesNotExist:
                return d["str"]
        for k, v in d.items():
            if isinstance(v, str):
                if (dt := dateparse.parse_datetime(v)) is not None:
                    d[k] = dt
                if (dt := dateparse.parse_date(v)) is not None:
                    d[k] = dt
        return d
