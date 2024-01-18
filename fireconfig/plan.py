from typing import List
from typing import Mapping

from cdk8s import DependencyVertex


def _vert_id(v):
    if v.value is None:
        return None
    return f"{v.value.chart.node.id}/{v.value.node.id}"


def walk_dep_graph(v: DependencyVertex, dag):
    assert v.value
    if not hasattr(v.value, "chart"):
        return dag

    vid = _vert_id(v)
    dag[vid]
    if len(v.outbound) == 0:
        dag[v.value.chart.node.id].append(vid)  # type: ignore

    for dep in v.outbound:
        dep_vid = _vert_id(dep)
        dag[dep_vid].append(vid)
        dag = walk_dep_graph(dep, dag)

    return dag


def write_mermaid_graph(dag: Mapping[str, List[str]]) -> str:
    node_ids = {}

    mermaid = "```mermaid\n"
    mermaid += "graph LR;\n"
    for (i, key) in enumerate(dag.keys()):
        parts = key.split("/")
        lparen = "([" if len(parts) == 1 else "["
        rparen = "])" if len(parts) == 1 else "]"
        node_ids[key] = i
        mermaid += f"  {i}{lparen}{parts[-1]}{rparen}\n"
    for start, edges in dag.items():
        for end in edges:
            mermaid += f"  {node_ids[start]}-->{node_ids[end]}\n"
    mermaid += "```\n"

    return mermaid
