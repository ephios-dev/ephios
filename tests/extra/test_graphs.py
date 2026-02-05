import pytest

from ephios.extra.graphs import DirectedGraph


@pytest.fixture
def graph1():
    return DirectedGraph({
        "RS": ["San"],
        "BF": ["WR", "BM"],
        "WR": ["San", "DRSA"],
        "BM": ["DRSA"],
        "DRSA": ["EH"],
        "NFS": ["RS"],
        "San": ["EH"],
        "GF": ["TF"],
        "ZF": ["GF"],
    })


@pytest.fixture
def cyclic_graph():
    return DirectedGraph({
        "A": ["B"],
        "B": ["C"],
        "C": ["A"],
    })


def test_directed_graph_contains(graph1):
    assert "NFS" in graph1
    assert "XX" not in graph1


def test_directed_graph_add_node(graph1):
    graph1.add("RH", ["San"], parents=["RS"])
    assert "RH" in graph1
    assert graph1.children("RH") == {"San"}
    assert graph1.parents("RH") == {"RS"}
    assert graph1.children("RS") == {"San", "RH"}
    assert graph1.ancestors("RH") == {"RS", "NFS"}
    assert graph1.descendants("RS") == {"San", "EH", "RH"}


def test_directed_graph_remove_edge(graph1):
    graph1.remove_edge("RS", "San")
    assert graph1.children("RS") == set()
    assert graph1.parents("San") == {"WR"}
    assert graph1.ancestors("San") == {"BF", "WR"}
    assert graph1.descendants("RS") == set()


def test_directed_graph_remove_node_briding_edges(graph1):
    graph1.remove_node("RS", bridge_edges=True)
    assert "RS" not in graph1
    assert graph1.children("NFS") == {"San"}
    assert graph1.parents("San") == {"NFS", "WR"}
    assert graph1.ancestors("San") == {"NFS", "BF", "WR"}
    assert graph1.descendants("NFS") == {"San", "EH"}


def test_directed_graph_remove_node_dicarding_edges(graph1):
    graph1.remove_node("RS", bridge_edges=False)
    assert "RS" not in graph1
    assert graph1.children("NFS") == set()
    assert graph1.parents("San") == {"WR"}
    assert graph1.ancestors("San") == {"BF", "WR"}
    assert graph1.descendants("NFS") == set()


def test_directed_graph_roots(graph1):
    assert graph1.roots() == {"NFS", "ZF", "BF"}


def test_directed_graph_remove_node_cyclic(cyclic_graph):
    cyclic_graph.remove_node("A")
    assert "A" not in cyclic_graph
    assert cyclic_graph.children("C") == {"B"}


def test_directed_graph_topological_sort(graph1):
    topo = graph1.topological_sort()
    assert topo.index("NFS") < topo.index("RS") < topo.index("San")
    assert topo.index("BF") < topo.index("WR")
    assert topo.index("BF") < topo.index("BM")
    assert topo.index("WR") < topo.index("DRSA")
    assert topo.index("BM") < topo.index("DRSA")
    assert topo.index("ZF") < topo.index("GF") < topo.index("TF")
    assert topo.index("EH") == len(topo) - 1


def test_directed_graph_topological_sort_small():
    assert DirectedGraph({}).topological_sort() == []
    assert DirectedGraph({"A": []}).topological_sort() == ["A"]


def test_directed_graph_topological_sort_cyclic(cyclic_graph):
    with pytest.raises(ValueError):
        cyclic_graph.topological_sort()
