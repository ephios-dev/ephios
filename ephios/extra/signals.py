from django.db.models.signals import post_save
from django.dispatch import receiver

from ephios.core.models import Qualification
from ephios.core.services.qualification import clear_universe_graph


@receiver(post_save, sender=Qualification)
def clear_universe_graph_on_qualification_change(sender, instance, **kwargs):
    clear_universe_graph()
