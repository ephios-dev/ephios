from copy import copy

from ephios.core.models import Qualification
from ephios.extra.graphs import DirectedGraph

_UNIVERSE_GRAPH = None


def _get_universe_graph():
    global _UNIVERSE_GRAPH
    if _UNIVERSE_GRAPH is None:
        _UNIVERSE_GRAPH = DirectedGraph(
            {
                qualification.uuid: [inc.uuid for inc in qualification.includes.all()]
                for qualification in Qualification.objects.all().prefetch_related("includes")
            }
        )
    return copy(_UNIVERSE_GRAPH)


def clear_universe_graph():
    global _UNIVERSE_GRAPH
    _UNIVERSE_GRAPH = None


def essential_set_of_qualifications(
    qualifications,
):
    """
    Compute a minimum set of qualifications that include every qualification in the given set, assuming
    all (transitive) inclusions from the given universe.
    """
    graph = _get_universe_graph()
    has_uuids = {qualification.uuid for qualification in qualifications}
    graph.keep_only(has_uuids)
    return {q for q in qualifications if q.uuid in graph.roots()}


def essential_set_of_qualifications_to_show_with_user(qualifications):
    """
    This function takes an iterable of qualifications and
    returns the qualifications that are essential in the
    given set and the category is meant to be shown with the user.
    """
    # this is a little tricky. Imagine the following situation:
    # - categories A and B with qualifications a2 > b2 > a1 > b1
    # - (> is inclusion); B should not be shown
    # - if we first filter for essential qualifications, we get b2
    #   then it would be wrong to filter out b2 as it's meant to not be shown
    # - if we instead first filter for qualifications that are shown with the user
    #   we get a2 and a1 and must keep both as essential
    #
    # Therefore we look at the roots of the graph of these qualifications
    # If the roots contain an element not to be shown, we remove it
    # from the graph and repead, until we can return roots that should
    # all be shown
    graph = _get_universe_graph()
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
    graph = _get_universe_graph()
    all_uuids = graph.spread_from([qualification.uuid for qualification in qualifications])
    return Qualification.objects.filter(uuid__in=all_uuids)


def uuids_of_qualifications_fulfilling_any_of(qualifications):
    """
    Return uuids of all qualifications fulfilling any of the given qualifications,
    assuming all (transitive) inclusions from the given universe.
    """
    graph = _get_universe_graph()
    return graph.spread_reverse([qualification.uuid for qualification in qualifications])
