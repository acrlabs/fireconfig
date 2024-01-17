from abc import ABCMeta
from abc import abstractmethod
from typing import Any
from typing import List
from typing import MutableMapping
from typing import Self

from cdk8s import ApiObject
from cdk8s import Chart
from constructs import Construct

from fireconfig import k8s

_STANDARD_NAMESPACES = [
    'default',
    'kube-node-lease',
    'kube-public',
    'kube-system',
]


class ObjectBuilder(metaclass=ABCMeta):
    def __init__(self: Self):
        self._annotations: MutableMapping[str, str] = {}
        self._labels: MutableMapping[str, str] = {}
        self._deps: List[ApiObject] = []

    def with_annotation(self, key: str, value: str) -> Self:
        self._annotations[key] = value
        return self

    def with_label(self, key: str, value: str) -> Self:
        self._labels[key] = value
        return self

    def with_dependencies(self, *deps: ApiObject) -> Self:
        self._deps.extend(deps)
        return self

    def build(self, namespace: str, chart: Chart):
        if namespace not in _STANDARD_NAMESPACES:
            ns = k8s.KubeNamespace(chart, "ns", metadata={"name": namespace})
            self._deps.insert(0, ns)

        meta: MutableMapping[str, Any] = {"namespace": namespace}
        if self._annotations:
            meta["annotations"] = self._annotations
        if self._labels:
            meta["labels"] = self._labels

        obj, *rest = self._build(namespace, k8s.ObjectMeta(**meta), chart)

        for d in self._deps:
            obj.add_dependency(d)

        return obj, *rest

    @abstractmethod
    def _build(self, namespace: str, meta: k8s.ObjectMeta, chart: Chart):
        ...


class NamespacedObject(metaclass=ABCMeta):
    _obj: ObjectBuilder
    ID: str

    def compile(self, namespace: str, app: Construct):
        chart = Chart(app, self.ID)
        self._obj.build(namespace, chart)
