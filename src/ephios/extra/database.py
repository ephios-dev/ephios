from django.db import connection
from django.utils.functional import lazy

# Shorthand for .select_for_update(of=("self,")) that handles DBS that don't support that feature
# https://docs.djangoproject.com/en/dev/ref/models/querysets/#django.db.models.query.QuerySet.select_for_update
OF_SELF = lazy(lambda: ("self",) if connection.features.has_select_for_update_of else (), tuple)()
