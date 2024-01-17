from cdk8s import App

from .container import ContainerBuilder
from .deployment import DeploymentBuilder
from .env import EnvBuilder
from .object import NamespacedObject
from .volume import VolumesBuilder

__all__ = [
    'ContainerBuilder',
    'DeploymentBuilder',
    'EnvBuilder',
    'NamespacedObject',
    'VolumesBuilder',
]


def build(namespace: str, *objs: NamespacedObject):
    app = App()

    for obj in objs:
        obj.compile(namespace, app)

    # ca = ClusterAutoscaler(app, skprov.get_grpc_address())
    # ca.add_dependency(skprov)

    app.synth()
