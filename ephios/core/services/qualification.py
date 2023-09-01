from django.core.cache import cache
from django.db.models.signals import m2m_changed, post_delete, post_save
from django.dispatch import receiver

from ephios.core.models import Qualification
from ephios.extra.graphs import DirectedGraph


class QualificationUniverse:
    """
    This class stores all qualifications and their inclusions as a graph.
    You can get a copy of the graph with get_graph() and use it to do computations on qualifications.
    The graph is invalidated after changes to qualifications.
    """

    cache_key = "ephios.core.services.qualification.QualificationUniverse.qualifications"

    @classmethod
    def get_graph(cls):
        return cls.build_graph(cls.get_qualifications())

    @classmethod
    def build_graph(cls, qualifications):
        return DirectedGraph(
            {
                qualification.uuid: [inc.uuid for inc in qualification.includes.all()]
                for qualification in qualifications
            }
        )

    @classmethod
    def get_qualifications(cls):
        def _get_qualifications():
            qs = Qualification.objects.all().prefetch_related("includes").select_related("category")
            bool(qs)  # force evaluation
            return qs

        return cache.get_or_set(cls.cache_key, _get_qualifications)

    @classmethod
    def clear(cls):
        cache.delete(cls.cache_key)


@receiver(post_save, sender=Qualification)
@receiver(post_delete, sender=Qualification)
@receiver(m2m_changed, sender=Qualification.includes.through)
def clear_universe_graph_on_request_finished(sender, instance, **kwargs):
    # The graph is invalidated after qualifications were saved, deleted or m2m relations changed.
    # This should cover most cases in regular use.
    QualificationUniverse.clear()


def top_level_set_of_qualifications(
    qualifications,
):
    """
    Compute a minimum set of qualifications that include every qualification in the given set, assuming
    all (transitive) inclusions from the given universe.
    """
    graph = QualificationUniverse.get_graph()
    has_uuids = {qualification.uuid for qualification in qualifications}
    graph.keep_only(has_uuids)
    return {q for q in qualifications if q.uuid in graph.roots()}


def essential_set_of_qualifications(qualifications):
    """
    This function takes an iterable of qualifications and
    returns the qualifications that are essential in the
    given set while the category is meant to be shown with the user.
    """
    # This is not a trivial concatenation of top_level and show_with_user filter!
    # Imagine the following situation:
    # - categories A and B with qualifications a2 > b2 > a1 > b1
    # - (> is inclusion); B should not be shown
    # - if we first filter for essential qualifications, we get b2
    #   then it would be wrong to filter out b2 as it's meant to not be shown
    # - if we instead first filter for qualifications that are shown with the user
    #   we get a2 and a1 and must keep both as essential
    #
    # Therefore we look at the roots of the graph of these qualifications
    # If the roots contain an element not to be shown, we remove it
    # from the graph and repeat, until we can return roots that should
    # all be shown
    graph = QualificationUniverse.get_graph()
    qualifications = set(qualifications)
    graph.keep_only({qualification.uuid for qualification in qualifications})

    while graph:
        root_qualifications = {q for q in qualifications if q.uuid in graph.roots()}
        did_remove = False
        for q in root_qualifications:
            if not q.category.show_with_user:
                graph.remove_node(q.uuid)
                did_remove = True
        if not did_remove:
            return root_qualifications
    return set()


def collect_all_included_qualifications(qualifications):
    """
    Compute the set of all qualifications that are included in the given set of qualifications, assuming
    all (transitive) inclusions from the given universe.
    """
    graph = QualificationUniverse.get_graph()
    all_uuids = graph.spread_from([qualification.uuid for qualification in qualifications])
    return Qualification.objects.filter(uuid__in=all_uuids)


def uuids_of_qualifications_fulfilling_any_of(qualifications):
    """
    Return uuids of all qualifications fulfilling any of the given qualifications,
    assuming all (transitive) inclusions from the given universe.
    """
    graph = QualificationUniverse.get_graph()
    return graph.spread_reverse([qualification.uuid for qualification in qualifications])
