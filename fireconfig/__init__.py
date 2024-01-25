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
from fireconfig.output import format_diff
from fireconfig.output import format_mermaid_graph
from fireconfig.plan import GLOBAL_CHART_NAME
from fireconfig.plan import compute_diff
from fireconfig.plan import find_deleted_nodes
from fireconfig.plan import get_resource_changes
from fireconfig.plan import walk_dep_graph
from fireconfig.subgraph import ChartSubgraph
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


def compile(pkgs: T.Dict[str, T.List[AppPackage]], dag_filename: T.Optional[str] = None) -> T.Tuple[str, str]:
    app = App()
    gl = Chart(app, GLOBAL_CHART_NAME, disable_resource_name_hashes=True)

    subgraph_dag = defaultdict(list)
    subgraphs = {}
    subgraphs[GLOBAL_CHART_NAME] = ChartSubgraph(GLOBAL_CHART_NAME)

    for ns, pkglist in pkgs.items():
        add_missing_namespace(gl, ns)
        for pkg in pkglist:
            chart = Chart(app, pkg.id, namespace=ns, disable_resource_name_hashes=True)
            chart.add_dependency(gl)
            pkg.compile(chart)

            fix_cluster_scoped_objects(chart)
            subgraphs[pkg.id] = ChartSubgraph(pkg.id)
            subgraph_dag[gl.node.id].append(pkg.id)

    for obj in DependencyGraph(app.node).root.outbound:
        walk_dep_graph(obj, subgraphs)
    diff, kinds = compute_diff(app)
    resource_changes = get_resource_changes(diff, kinds)

    try:
        find_deleted_nodes(subgraphs, resource_changes, dag_filename)
    except Exception as e:
        print(f"WARNING: {e}\nCould not read old DAG file, graph may be missing deleted nodes")

    graph_str = format_mermaid_graph(subgraph_dag, subgraphs, dag_filename, resource_changes)
    diff_str = format_diff(resource_changes)

    # app.synth()

    return graph_str, diff_str
