import re
import typing as T
from glob import glob

import yaml
from cdk8s import ApiObject
from cdk8s import App
from cdk8s import DependencyVertex
from deepdiff import DeepDiff  # type: ignore

from fireconfig.util import is_cluster_scoped

DAG = T.MutableMapping[T.Tuple[str, str], T.List[str]]
GLOBAL_CHART_NAME = "global"


def _namespaced_or_chart_name_from_dict(obj: T.Mapping[str, T.Any], chart: str) -> str:
    prefix = obj["metadata"].get("namespace")
    if prefix is None or is_cluster_scoped(obj["kind"]):
        prefix = chart
    return prefix + "/" + obj["metadata"]["name"]


def _namespaced_or_chart_name(obj: ApiObject) -> str:
    prefix = obj.metadata.namespace
    if prefix is None or is_cluster_scoped(obj.kind):
        prefix = obj.chart.node.id
    return prefix + "/" + obj.name


def _node_label_for(obj: DependencyVertex):
    assert obj.value

    ty = type(obj.value).__name__.replace("Kube", "")
    return f"<b>{ty}</b><br>{obj.value.node.id}"


def compute_diff(app: App) -> T.Mapping[str, T.Any]:
    old_defs = {}
    for filename in glob(f"{app.outdir}/*{app.output_file_extension}"):
        with open(filename) as f:
            parsed_filename = re.match(app.outdir + r"\/(\d{4}-)?(.*)" + app.output_file_extension, filename)
            old_chart = "UNKNOWN"
            if parsed_filename:
                old_chart = parsed_filename.group(2)
            for old_obj in yaml.safe_load_all(f):
                node_id = _namespaced_or_chart_name_from_dict(old_obj, old_chart)
                old_defs[node_id] = old_obj

    new_defs = {}
    for chart in app.charts:
        for new_obj in chart.api_objects:
            node_id = _namespaced_or_chart_name(new_obj)
            new_defs[node_id] = new_obj.to_json()

    return DeepDiff(old_defs, new_defs, view="tree")


def walk_dep_graph(v: DependencyVertex, dag: DAG):
    assert v.value
    if not hasattr(v.value, "chart"):
        return dag

    vid = _namespaced_or_chart_name(T.cast(ApiObject, v.value))
    label = _node_label_for(v)
    dag[(vid, label)]  # defaultdict, so this creates the entry if it doesn't exist

    if len(v.outbound) == 0:
        chart = v.value.chart.node.id  # type: ignore
        dag[(chart, chart)].append(vid)

    for dep in v.outbound:
        assert dep.value
        dep_vid = _namespaced_or_chart_name(T.cast(ApiObject, dep.value))
        dep_label = _node_label_for(dep)
        dag[(dep_vid, dep_label)].append(vid)
        dag = walk_dep_graph(dep, dag)

    return dag
