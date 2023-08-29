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


def collect_all_included_qualifications(qualifications):
    """
    Compute the set of all qualifications that are included in the given set of qualifications, assuming
    all (transitive) inclusions from the given universe.
    """
    graph = _get_universe_graph()
    all_uuids = graph.spread_from([qualification.uuid for qualification in qualifications])
    return Qualification.objects.filter(uuid__in=all_uuids)
