from abc import ABCMeta
from abc import abstractmethod
from typing import Any
from typing import List
from typing import MutableMapping
from typing import Self

from cdk8s import ApiObject
from cdk8s import Chart

from fireconfig import k8s


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

    def build(self, chart: Chart):
        meta: MutableMapping[str, Any] = {}
        if self._annotations:
            meta["annotations"] = self._annotations
        if self._labels:
            meta["labels"] = self._labels

        obj = self._build(k8s.ObjectMeta(**meta), chart)

        for d in self._deps:
            obj.add_dependency(d)

        return obj

    @abstractmethod
    def _build(self, meta: k8s.ObjectMeta, chart: Chart):
        ...
