import re
import typing as T
from glob import glob

import yaml
from cdk8s import App
from cdk8s import DependencyVertex
from deepdiff import DeepDiff  # type: ignore

from fireconfig import k8s

DAG = T.MutableMapping[T.Tuple[str, str], T.List[str]]
GLOBAL_CHART_NAME = "global"


def _namespaced_or_chart_name(obj: T.Mapping[str, T.Any], chart: str) -> str:
    return obj["metadata"].get("namespace", chart) + "/" + obj["metadata"]["name"]


def compute_diff(app: App) -> T.Mapping[str, T.Any]:
    old_defs = {}
    for filename in glob(f"{app.outdir}/*{app.output_file_extension}"):
        with open(filename) as f:
            parsed_filename = re.match(app.outdir + r"\/(\d{4}-)?(.*)" + app.output_file_extension, filename)
            old_chart = "UNKNOWN"
            if parsed_filename:
                old_chart = parsed_filename.group(2)
            for old_obj in yaml.safe_load_all(f):
                node_id = _namespaced_or_chart_name(old_obj, old_chart)
                old_defs[node_id] = old_obj

    new_defs = {}
    for chart in app.charts:
        for new_obj in chart.to_json():
            node_id = _namespaced_or_chart_name(new_obj, chart.node.id)
            new_defs[node_id] = new_obj

    return DeepDiff(old_defs, new_defs, view="tree")


def _vert_id(v):
    if v.value.metadata.namespace:
        return f"{v.value.metadata.namespace}/{v.value.name}"
    elif isinstance(v.value, k8s.KubeNamespace):
        return f"{GLOBAL_CHART_NAME}/{v.value.name}"
    return v.value.name


def walk_dep_graph(v: DependencyVertex, dag: DAG):
    assert v.value
    if not hasattr(v.value, "chart"):
        return dag

    vid = _vert_id(v)
    label = v.value.node.id
    dag[(vid, label)]
    if len(v.outbound) == 0:
        chart = v.value.chart.node.id  # type: ignore
        dag[(chart, chart)].append(vid)

    for dep in v.outbound:
        assert dep.value
        dep_vid = _vert_id(dep)
        dep_label = dep.value.node.id
        dag[(dep_vid, dep_label)].append(vid)
        dag = walk_dep_graph(dep, dag)

    return dag
