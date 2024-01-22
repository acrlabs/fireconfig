import re
import typing as T
from enum import Enum

import simplejson as json
from deepdiff.helper import notpresent  # type: ignore

from fireconfig.plan import DAG

_DELETED_OBJS_START = "%% DELETED OBJECTS START"
_DELETED_OBJS_END = "%% DELETED OBJECTS END"
_STYLE_DEFS_START = "%% STYLE DEFINITIONS START"
_STYLE_DEFS_END = "%% STYLE DEFINITIONS END"


# Colors taken from https://personal.sron.nl/~pault/#sec:qualitative
class NodeState(Enum):
    Changed = "#6ce"
    ChangedWithPodRecreate = "#cb4"
    Added = "#283"
    Removed = "#e67"


def _get_node_state(change_type, path: str, curr_state: T.Optional[NodeState]) -> NodeState:
    if curr_state and curr_state != NodeState.Changed:
        return curr_state

    if change_type == "dictionary_item_removed":
        return NodeState.Removed if path == "root" else NodeState.Changed
    elif change_type == "dictionary_item_added":
        return NodeState.Added if path == "root" else NodeState.Changed
    else:
        return NodeState.Changed


def format_graph_and_diff(dag: DAG, old_dag_filename: T.Optional[str], diff: T.Mapping[str, T.Any]) -> T.Tuple[str, str]:
    node_states: T.Dict[str, NodeState] = {}

    diff_details = ""
    mermaid = "```mermaid\n"
    mermaid += "graph LR;\n"
    for node, label in dag.keys():
        parts = node.split("/")
        lparen = "([" if len(parts) == 1 else "["
        rparen = "])" if len(parts) == 1 else "]"
        mermaid += f"  {node}{lparen}{label}{rparen}\n"
    for (start, _), edges in dag.items():
        for end in edges:
            mermaid += f"  {start}-->{end}\n"

    old_dag_lines = []
    deleted_obj_lines = set()
    if old_dag_filename:
        try:
            with open(old_dag_filename) as f:
                del_lines = False
                style_lines = False

                for l in f.readlines():
                    if l.startswith(_DELETED_OBJS_START):
                        del_lines = True
                    elif l.startswith(_DELETED_OBJS_END):
                        del_lines = False
                    elif l.startswith(_STYLE_DEFS_START):
                        style_lines = True
                    elif l.startswith(_STYLE_DEFS_END):
                        style_lines = False
                    elif not (del_lines or style_lines):
                        old_dag_lines.append(l)
        except Exception as e:
            print(f"WARNING: {e}\nCould not read old DAG file, graph may be missing deleted nodes")

    for change_type, items in diff.items():
        for i in items:
            root_item = i.path(output_format="list")[0]
            path = re.sub(r"\[" + f"'{root_item}'" + r"\]", "", i.path())
            node_state = _get_node_state(change_type, path, node_states.get(root_item))
            node_states[root_item] = node_state
            if node_state == NodeState.Removed:
                for l in old_dag_lines:
                    if root_item in l:
                        deleted_obj_lines.add(l)
            obj1_str = json.dumps(i.t1, indent='  ') if i.t1 != notpresent else i.t1
            obj2_str = json.dumps(i.t2, indent='  ') if i.t2 != notpresent else i.t2
            diff_details += f"<details><summary>\n\n#### {root_item}: {node_state.name}\n\n</summary>\n\n"
            diff_details += f"```\n{path}:\n{obj1_str} --> {obj2_str}\n```\n\n</details>\n"

    mermaid += f"{_DELETED_OBJS_START}\n"
    for del_line in deleted_obj_lines:
        mermaid += del_line
    mermaid += f"{_DELETED_OBJS_END}\n"

    mermaid += f"{_STYLE_DEFS_START}\n"
    for key, state in node_states.items():
        mermaid += f"  style {key} fill:{state.value},color:#000\n"
    mermaid += f"{_STYLE_DEFS_END}\n"
    mermaid += "```\n\n"

    return mermaid, diff_details
