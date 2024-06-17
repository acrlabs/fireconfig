from cdk8s import Chart

from fireconfig import k8s

_STANDARD_NAMESPACES = [
    "default",
    "kube-node-lease",
    "kube-public",
    "kube-system",
]


def add_missing_namespace(gl: Chart, ns: str):
    parent = gl.node.id
    if ns not in _STANDARD_NAMESPACES:
        k8s.KubeNamespace(gl, ns, metadata={"name": ns})
        parent = f"{gl.node.id}/{ns}"
    return parent
