import re
import typing as T
from collections import defaultdict
from enum import Enum
from glob import glob

import yaml
from cdk8s import App
from cdk8s import DependencyVertex
from deepdiff import DeepDiff  # type: ignore
from deepdiff.helper import notpresent  # type: ignore

from fireconfig.subgraph import ChartSubgraph
from fireconfig.util import owned_name
from fireconfig.util import owned_name_from_dict

GLOBAL_CHART_NAME = "global"
DELETED_OBJS_START = "%% DELETED OBJECTS START"
DELETED_OBJS_END = "%% DELETED OBJECTS END"
STYLE_DEFS_START = "%% STYLE DEFINITIONS START"
STYLE_DEFS_END = "%% STYLE DEFINITIONS END"

ChangeTuple = T.Tuple[str, T.Union[T.Mapping, notpresent], T.Union[T.Mapping, notpresent]]


# Colors taken from https://personal.sron.nl/~pault/#sec:qualitative
class ResourceState(Enum):
    Unchanged = ""
    Changed = "#6ce"
    ChangedWithPodRecreate = "#cb4"
    Added = "#283"
    Removed = "#e67"
    Unknown = "#f00"


class ResourceChanges:
    def __init__(self) -> None:
        self._state: ResourceState = ResourceState.Unchanged
        self._changes: T.List[ChangeTuple] = []

    @property
    def state(self) -> ResourceState:
        return self._state

    @property
    def changes(self) -> T.List[ChangeTuple]:
        return self._changes

    def update_state(self, change_type: str, path: str, kind: T.Optional[str]):
        if self._state in {ResourceState.Added, ResourceState.Removed}:
            return

        if path == "root":
            if change_type == "dictionary_item_removed":
                self._state = ResourceState.Removed
            elif change_type == "dictionary_item_added":
                self._state = ResourceState.Added
            else:
                self._state = ResourceState.Unknown
        elif self._state == ResourceState.ChangedWithPodRecreate:
            return
        elif kind == "Deployment":
            # TODO - this is obviously incomplete, it will not detect all cases
            # when pod recreation happens
            if (
                path.startswith("root['spec']['template']['spec']")
                or path.startswith("root['spec']['selector']")
            ):
                self._state = ResourceState.ChangedWithPodRecreate
            else:
                self._state = ResourceState.Changed
        else:
            self._state = ResourceState.Changed

    def add_change(self, path: str, r1: T.Union[T.Mapping, notpresent], r2: T.Union[T.Mapping, notpresent]):
        self._changes.append((path, r1, r2))


def compute_diff(app: App) -> T.Tuple[T.Mapping[str, T.Any], T.Mapping[str, str]]:
    kinds = {}
    old_defs = {}
    for filename in glob(f"{app.outdir}/*{app.output_file_extension}"):
        with open(filename) as f:
            parsed_filename = re.match(app.outdir + r"\/(\d{4}-)?(.*)" + app.output_file_extension, filename)
            old_chart = "UNKNOWN"
            if parsed_filename:
                old_chart = parsed_filename.group(2)
            for old_obj in yaml.safe_load_all(f):
                node_id = owned_name_from_dict(old_obj, old_chart)
                old_defs[node_id] = old_obj

    new_defs = {}
    for chart in app.charts:
        for new_obj in chart.api_objects:
            node_id = owned_name(new_obj)
            new_defs[node_id] = new_obj.to_json()
            kinds[node_id] = new_obj.kind

    return DeepDiff(old_defs, new_defs, view="tree"), kinds


def walk_dep_graph(v: DependencyVertex, subgraphs: T.Mapping[str, ChartSubgraph]):
    assert v.value
    if not hasattr(v.value, "chart"):
        return

    chart = v.value.chart.node.id  # type: ignore
    subgraphs[chart].add_node(v)

    for dep in v.outbound:
        assert dep.value
        if not hasattr(v.value, "chart"):
            return

        subgraphs[chart].add_edge(dep, v)
        walk_dep_graph(dep, subgraphs)


def get_resource_changes(diff: T.Mapping[str, T.Any], kinds: T.Mapping[str, str]) -> T.Mapping[str, ResourceChanges]:
    resource_changes: T.MutableMapping[str, ResourceChanges] = defaultdict(lambda: ResourceChanges())
    for change_type, items in diff.items():
        for i in items:
            root_item = i.path(output_format="list")[0]
            path = re.sub(r"\[" + f"'{root_item}'" + r"\]", "", i.path())
            resource_changes[root_item].update_state(change_type, path, kinds.get(root_item))
            resource_changes[root_item].add_change(path, i.t1, i.t2)

    return resource_changes


def find_deleted_nodes(
    subgraphs: T.Mapping[str, ChartSubgraph],
    resource_changes: T.Mapping[str, ResourceChanges],
    old_dag_filename: T.Optional[str],
):
    if not old_dag_filename:
        return

    old_dag_lines = []
    with open(old_dag_filename) as f:
        current_chart = None
        del_lines = False

        for l in f.readlines():
            chart_match = re.match("^\s*subgraph (.*)", l)
            if chart_match:
                current_chart = chart_match.group(1)
            elif re.match("^\s*end$", l):
                current_chart = None
            if l.startswith(DELETED_OBJS_START):
                del_lines = True
            elif l.startswith(DELETED_OBJS_END):
                del_lines = False
            elif current_chart is not None and not del_lines:
                old_dag_lines.append((current_chart, l))

    for res, changes in resource_changes.items():
        if changes.state == ResourceState.Removed:
            for chart, l in old_dag_lines:
                if res in l:
                    subgraphs[chart].add_deleted_line(l)
