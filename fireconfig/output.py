import typing as T

import simplejson as json
from deepdiff.helper import notpresent  # type: ignore

from fireconfig.plan import DELETED_OBJS_END
from fireconfig.plan import DELETED_OBJS_START
from fireconfig.plan import STYLE_DEFS_END
from fireconfig.plan import STYLE_DEFS_START
from fireconfig.plan import ResourceChanges
from fireconfig.plan import ResourceState
from fireconfig.subgraph import ChartSubgraph


def _format_node_label(n: str, ty: str) -> str:
    name = n.split("/")[-1]
    return f"  {n}[<b>{ty}</b><br>{name}]\n"


def format_mermaid_graph(
    subgraph_dag: T.Mapping[str, T.List[str]],
    subgraphs: T.Mapping[str, ChartSubgraph],
    old_dag_filename: T.Optional[str],
    resource_changes: T.Mapping[str, ResourceChanges],
) -> str:

    mermaid = "```mermaid\n"
    mermaid += "%%{init: {'themeVariables': {'mainBkg': '#ddd'}}}%%\n"
    mermaid += "graph LR\n\n"

    # Colors taken from https://personal.sron.nl/~pault/#sec:qualitative
    mermaid += "classDef default color:#000\n"

    for chart, sg in subgraphs.items():
        mermaid += f"subgraph {chart}\n"
        mermaid += "  direction LR\n"
        for n, ty in sg.nodes():
            mermaid += _format_node_label(n, ty)

        for s, e in sg.edges():
            mermaid += f"  {s}--->{e}\n"

        mermaid += f"{DELETED_OBJS_START}\n"
        for del_line in sg.deleted_lines():
            mermaid += del_line
        mermaid += f"{DELETED_OBJS_END}\n"
        mermaid += "end\n\n"

    for sg1, edges in subgraph_dag.items():
        for sg2 in edges:
            mermaid += f"{sg1}--->{sg2}\n"

    mermaid += f"\n{STYLE_DEFS_START}\n"
    for res, changes in resource_changes.items():
        if changes.state != ResourceState.Unchanged:
            mermaid += f"  style {res} fill:{changes.state.value}\n"
    mermaid += f"{STYLE_DEFS_END}\n"
    mermaid += "```\n\n"

    return mermaid


def format_diff(resource_changes: T.Mapping[str, ResourceChanges]) -> str:
    diff_details = ""

    for res, c in sorted(resource_changes.items()):
        diff_details += f"<details><summary>\n\n#### {res}: {c.state.name}\n\n</summary>\n\n"
        for path, r1, r2 in c.changes:
            r1_str = json.dumps(r1, indent='  ') if r1 != notpresent else r1
            r2_str = json.dumps(r2, indent='  ') if r2 != notpresent else r2
            diff_details += f"```\n{path}:\n{r1_str} --> {r2_str}\n```\n\n"
        diff_details += "</details>\n"

    return diff_details
