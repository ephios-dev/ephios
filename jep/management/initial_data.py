volunteers = Group.objects.create(name=_("Volunteers"))
volunteers.user_set.add(user)
volunteers.save()

planners = Group.objects.create(name=_("Planners"))
planners.user_set.add(user)
planners.save()

assign_perm("publish_event_for_group", planners, volunteers)
from django.contrib.auth.models import Permission, Group

all_perms = list(Permission.objects.all())

assign_perm("event_management.add_event", planners)
assign_perm("event_management.delete_event", planners)