import typing as T
from abc import ABCMeta
from abc import abstractmethod

from cdk8s import ApiObject
from cdk8s import Chart

from fireconfig import k8s


class ObjectBuilder(metaclass=ABCMeta):
    def __init__(
        self: T.Self,
        annotations: T.MutableMapping[str, T.Any] = dict(),
        labels: T.MutableMapping[str, T.Any] = dict(),
    ):
        self._annotations: T.MutableMapping[str, str] = annotations
        self._labels: T.MutableMapping[str, str] = labels
        self._deps: T.List[ApiObject] = []

    def with_annotation(self, key: str, value: str) -> T.Self:
        self._annotations[key] = value
        return self

    def with_label(self, key: str, value: str) -> T.Self:
        self._labels[key] = value
        return self

    def with_dependencies(self, *deps: ApiObject) -> T.Self:
        self._deps.extend(deps)
        return self

    def build(self, chart: Chart):
        meta: T.MutableMapping[str, T.Any] = {}
        if self._annotations:
            meta["annotations"] = self._annotations
        if self._labels:
            meta["labels"] = self._labels

        obj = self._build(k8s.ObjectMeta(**meta), chart)

        for d in self._deps:
            obj.add_dependency(d)

        return obj

    @abstractmethod
    def _build(self, meta: k8s.ObjectMeta, chart: Chart): ...
