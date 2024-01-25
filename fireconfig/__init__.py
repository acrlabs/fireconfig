import typing as T
from abc import ABCMeta
from abc import abstractmethod
from collections import defaultdict

from cdk8s import App
from cdk8s import Chart
from cdk8s import DependencyGraph
from constructs import Construct

from fireconfig.container import ContainerBuilder
from fireconfig.deployment import DeploymentBuilder
from fireconfig.env import EnvBuilder
from fireconfig.namespace import add_missing_namespace
from fireconfig.output import format_graph_and_diff
from fireconfig.plan import GLOBAL_CHART_NAME
from fireconfig.plan import compute_diff
from fireconfig.plan import walk_dep_graph
from fireconfig.util import fix_cluster_scoped_objects
from fireconfig.volume import VolumesBuilder

__all__ = [
    'ContainerBuilder',
    'DeploymentBuilder',
    'EnvBuilder',
    'VolumesBuilder',
]


class AppPackage(metaclass=ABCMeta):
    @property
    @abstractmethod
    def id(self):
        ...

    @abstractmethod
    def compile(self, app: Construct):
        ...


def compile(pkgs: T.Dict[str, T.List[AppPackage]], dag_filename: T.Optional[str]) -> T.Tuple[str, str]:
    app = App()
    gl = Chart(app, GLOBAL_CHART_NAME, disable_resource_name_hashes=True)

    dag = defaultdict(list)
    for ns, pkglist in pkgs.items():
        parent = add_missing_namespace(gl, ns)
        for pkg in pkglist:
            chart = Chart(app, pkg.id, namespace=ns, disable_resource_name_hashes=True)
            chart.add_dependency(gl)
            pkg.compile(chart)

            fix_cluster_scoped_objects(chart)

            dag[(parent, ns)].append(pkg.id)

    for obj in DependencyGraph(app.node).root.outbound:
        dag = walk_dep_graph(obj, dag)

    diff = compute_diff(app)
    graph_str, diff_str = format_graph_and_diff(dag, dag_filename, diff)

    app.synth()

    return graph_str, diff_str
