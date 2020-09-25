import json

from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Model, QuerySet
from django.utils import dateparse


class CustomJSONEncoder(DjangoJSONEncoder):
    def default(self, obj):
        if isinstance(obj, QuerySet):
            return list(obj)
        elif isinstance(obj, Model):
            return obj.pk
        else:
            return super().default(obj)


class CustomJSONDecoder(json.JSONDecoder):
    def __init__(self, *args, **kargs):
        super().__init__(*args, object_hook=self.custom_hook, **kargs)

    def custom_hook(self, d):
        for k, v in d.items():
            if isinstance(v, str):
                if (dt := dateparse.parse_datetime(v)) is not None:
                    d[k] = dt
                if (dt := dateparse.parse_date(v)) is not None:
                    d[k] = dt
        return d
