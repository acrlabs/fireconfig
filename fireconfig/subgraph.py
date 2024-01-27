import typing as T
from collections import defaultdict

from cdk8s import ApiObject
from cdk8s import DependencyVertex

from fireconfig.util import owned_name


class ChartSubgraph:
    def __init__(self, name: str) -> None:
        self._name = name
        self._dag: T.MutableMapping[str, T.List[str]] = defaultdict(list)
        self._kinds: T.MutableMapping[str, str] = {}
        self._deleted_lines: T.Set[str] = set()

    def add_node(self, v: DependencyVertex) -> str:
        obj = T.cast(ApiObject, v.value)
        name = owned_name(obj)
        self._kinds[name] = obj.kind
        self._dag[name]
        return name

    def add_edge(self, s: DependencyVertex, t: DependencyVertex):
        s_name = self.add_node(s)
        t_name = self.add_node(t)
        self._dag[s_name].append(t_name)

    def add_deleted_line(self, l: str):
        self._deleted_lines.add(l)

    def nodes(self) -> T.List[T.Tuple[str, str]]:
        return [(n, self._kinds[n]) for n in self._dag.keys()]

    def edges(self) -> T.List[T.Tuple[str, str]]:
        return [(s, e) for s, l in self._dag.items() for e in l]

    def deleted_lines(self) -> T.Iterable[str]:
        return self._deleted_lines
