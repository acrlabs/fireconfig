"""
The bulk of the logic for computing the plan (a la terraform plan) lives in this file.
The rough outline of steps taken is

1. For each chart, walk the dependency graph to construct a DAG (`walk_dep_graph`)
2. Compute a diff between the newly-generated manifests and the old ones (`compute_diff`)
3. Turn that diff into a list of per-resource changes (`get_resource_changes`)
4. Find out what's been deleted since the last run and add that into the graph (`find_deleted_nodes`)
"""

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
        """
        Given a particular resource, update the state (added, removed, changed, etc) for
        that resource.  We use the list of "change types" from DeepDiff defined here:

        https://github.com/seperman/deepdiff/blob/89c5cc227c48b63be4a0e1ad4af59d3c1b0272d7/deepdiff/serialization.py#L388

        Since these are Kubernetes objects, we expect the root object to be a dictionary, if it's
        not, something has gone horribly wrong.  If the root object was added or removed, we mark the
        entire object as added or removed; otherwise if some sub-dictionary was added or removed,
        the root object was just "changed".

        We use the `kind` field to determine whether pod recreation needs to happen.  This entire
        function is currently very hacky and incomplete, it would be good to make this more robust sometime.
        """
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
            if path.startswith("root['spec']['template']['spec']") or path.startswith("root['spec']['selector']"):
                self._state = ResourceState.ChangedWithPodRecreate
            else:
                self._state = ResourceState.Changed
        else:
            self._state = ResourceState.Changed

    def add_change(self, path: str, r1: T.Union[T.Mapping, notpresent], r2: T.Union[T.Mapping, notpresent]):
        self._changes.append((path, r1, r2))


def compute_diff(app: App) -> T.Tuple[T.Mapping[str, T.Any], T.Mapping[str, str]]:
    """
    To compute a diff, we look at the old YAML files that were written out "last time", and
    compare them to the generated YAML by cdk8s "this time".
    """

    kinds = {}
    old_defs = {}
    for filename in glob(f"{app.outdir}/*{app.output_file_extension}"):
        with open(filename, encoding="utf-8") as f:
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

    # threshold_to_diff_deeper was added in deepdiff 8.0.0
    # threshold_to_diff_deeper=0 maintains previous behavior from <7.0.0
    return DeepDiff(old_defs, new_defs, view="tree",threshold_to_diff_deeper=0), kinds


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

        # Note that cdk8s does things backwards, so instead of adding the edge from v->dep,
        # we add an edge from dep->v
        subgraphs[chart].add_edge(dep, v)
        walk_dep_graph(dep, subgraphs)


def get_resource_changes(diff: T.Mapping[str, T.Any], kinds: T.Mapping[str, str]) -> T.Mapping[str, ResourceChanges]:
    resource_changes: T.MutableMapping[str, ResourceChanges] = defaultdict(ResourceChanges)
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
    """
    To determine the location and connections of deleted nodes in the DAG,
    we just look at the old DAG file and copy out the edge lines that contain the
    removed objects.  The DAG file is split into subgraphs, so we parse it line-by-line
    and only copy entries that are a) inside a subgraph block, and b) weren't marked as
    deleted "last time".  We use special comment markers in the DAG file to tell which
    things were deleted "last time".
    """
    if not old_dag_filename:
        return

    old_dag_lines = []
    with open(old_dag_filename, encoding="utf-8") as f:
        current_chart = None
        del_lines = False

        for ln in f.readlines():
            chart_match = re.match(r"^\s*subgraph (.*)", ln)
            if chart_match:
                current_chart = chart_match.group(1)
            elif re.match(r"^\s*end$", ln):
                current_chart = None
            if ln.startswith(DELETED_OBJS_START):
                del_lines = True
            elif ln.startswith(DELETED_OBJS_END):
                del_lines = False
            elif current_chart is not None and not del_lines:
                old_dag_lines.append((current_chart, ln))

    for res, changes in resource_changes.items():
        if changes.state == ResourceState.Removed:
            for chart, ln in old_dag_lines:
                if res in ln:
                    subgraphs[chart].add_deleted_line(ln)
