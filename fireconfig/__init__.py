from abc import ABCMeta
from abc import abstractmethod
from typing import Dict
from typing import List

from cdk8s import App
from cdk8s import Chart
from constructs import Construct

from fireconfig import k8s
from fireconfig.container import ContainerBuilder
from fireconfig.deployment import DeploymentBuilder
from fireconfig.env import EnvBuilder
from fireconfig.volume import VolumesBuilder

__all__ = [
    'ContainerBuilder',
    'DeploymentBuilder',
    'EnvBuilder',
    'VolumesBuilder',
]


_STANDARD_NAMESPACES = [
    'default',
    'kube-node-lease',
    'kube-public',
    'kube-system',
]


class AppPackage(metaclass=ABCMeta):
    @property
    @abstractmethod
    def id(self):
        ...

    @abstractmethod
    def compile(self, app: Construct):
        ...


def compile(pkgs: Dict[str, List[AppPackage]]):
    app = App()
    gl = Chart(app, "global")

    for ns, pkglist in pkgs.items():
        if ns not in _STANDARD_NAMESPACES:
            k8s.KubeNamespace(gl, ns, metadata={"name": ns})
        for pkg in pkglist:
            chart = Chart(app, pkg.id, namespace=ns)
            chart.add_dependency(gl)
            pkg.compile(chart)

    app.synth()
