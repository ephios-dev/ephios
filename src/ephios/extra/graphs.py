import itertools
from collections import Counter, defaultdict
from typing import Optional


class DirectedGraph:
    """
    This class implements a directed graph using adjacency collections.
    """

    def __init__(self, edges: Optional[dict] = None):
        self.adjancent_nodes: dict = {}
        if edges is not None:
            for node, children in edges.items():
                self.add(node, children)

    def add(self, node, children=None, parents=None):
        """
        Add a node to the graph, with the given children.
        If the node already exists, the children are added to the existing ones.
        Children or parents not already in the graph are added as well.
        """
        if node not in self.adjancent_nodes:
            self.adjancent_nodes[node] = set()
        if children is not None:
            for child in children:
                self.adjancent_nodes[node].add(child)
                if child not in self.adjancent_nodes:
                    self.adjancent_nodes[child] = set()
        if parents is not None:
            for parent in parents:
                if parent not in self.adjancent_nodes:
                    self.adjancent_nodes[parent] = {node}
                else:
                    self.adjancent_nodes[parent].add(node)

    def nodes(self):
        return set(self.adjancent_nodes.keys())

    def children(self, node):
        return self.adjancent_nodes[node]

    def parents(self, node):
        return set(parent for parent, children in self.adjancent_nodes.items() if node in children)

    def remove_edge(self, node, child):
        """Remove an edge from the graph, throwing KeyError if it does not exist."""
        self.adjancent_nodes[node].remove(child)

    def descendants(self, node):
        """Return all nodes that are reachable from the given node excluding the node itself."""
        return self._bfs([node], extend_with=self.children) - {node}

    def ancestors(self, node):
        """Return all nodes that can reach the given node excluding the node itself."""
        return self._bfs([node], extend_with=self.parents) - {node}

    def spread_from(self, nodes):
        """
        Return all nodes that are reachable from the given nodes.
        """
        return self._bfs(nodes, extend_with=self.children)

    def spread_reverse(self, nodes):
        """
        Return all nodes that can reach any of the given nodes.
        """
        return self._bfs(nodes, extend_with=self.parents)

    def _bfs(self, starts, extend_with):
        """
        Return all nodes reachable starting at the given nodes.
        Use `extend_with` to define what nodes to expand to.
        """
        visited = set()
        queue = list(starts)
        while queue:
            node = queue.pop(0)
            if node not in visited:
                visited.add(node)
                queue.extend(extend_with(node))
        return visited

    def topological_sort(self):
        """
        Return a topological sort of the graph.
        Throws a ValueError if the graph contains cycles.
        """
        graph = self.adjancent_nodes.copy()
        in_degree = defaultdict(int)
        for node, children in graph.items():
            for child in children:
                in_degree[child] += 1
        queue = [node for node in graph if in_degree[node] == 0]
        result = []
        while queue:
            node = queue.pop()
            result.append(node)
            for child in graph[node]:
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)
        if len(result) != len(graph):
            raise ValueError("Graph contains cycles")
        return result

    def is_acyclic(self):
        """Return True if the graph is acyclic."""
        try:
            self.topological_sort()
        except ValueError:
            return False
        return True

    def roots(self):
        """Return all nodes that have no parents."""
        parent_counter = Counter(itertools.chain(*self.adjancent_nodes.values()))
        return {node for node in self.nodes() if parent_counter[node] == 0}

    def keep_only(self, nodes, bridge_edges=True):
        """Remove all nodes that are not in the given set."""
        for node in self.nodes() - set(nodes):
            self.remove_node(node, bridge_edges=bridge_edges)

    def remove_node(self, node, bridge_edges=True):
        """Remove a node from the graph, by default keeping the edges intact."""
        children = self.adjancent_nodes[node]
        for parent in self.parents(node):
            if bridge_edges:
                self.adjancent_nodes[parent] |= children
            self.adjancent_nodes[parent].remove(node)
        del self.adjancent_nodes[node]

    def __copy__(self):
        return DirectedGraph(self.adjancent_nodes)

    def __eq__(self, other):
        return self.adjancent_nodes == other.adjancent_nodes

    def __repr__(self):
        return f"DirectedGraph({self.adjancent_nodes})"

    def __str__(self):
        return repr(self)

    def __hash__(self):
        return hash(repr(self))

    def __bool__(self):
        return bool(self.adjancent_nodes)

    def __len__(self):
        return len(self.adjancent_nodes)

    def __iter__(self):
        return iter(self.adjancent_nodes)

    def __contains__(self, node):
        return node in self.adjancent_nodes
