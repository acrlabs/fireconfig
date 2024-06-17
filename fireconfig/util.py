import typing as T

from cdk8s import ApiObject
from cdk8s import Chart
from cdk8s import JsonPatch


# cdk8s incorrectly adds namespaces to cluster-scoped objects, so this function corrects for that
# (see https://github.com/cdk8s-team/cdk8s/issues/1618 and https://github.com/cdk8s-team/cdk8s/issues/1558)
def fix_cluster_scoped_objects(chart: Chart):
    for obj in chart.api_objects:
        if is_cluster_scoped(obj.kind):
            obj.add_json_patch(JsonPatch.remove("/metadata/namespace"))


def is_cluster_scoped(kind: str) -> bool:
    # Taken from a vanilla 1.27 kind cluster
    return kind in {
        "APIService",
        "CertificateSigningRequest",
        "ClusterRole",
        "ClusterRoleBinding",
        "ComponentStatus",
        "CSIDriver",
        "CSINode",
        "CustomResourceDefinition",
        "FlowSchema",
        "IngressClass",
        "MutatingWebhookConfiguration",
        "Namespace",
        "Node",
        "PriorityClass",
        "PriorityLevelConfiguration",
        "RuntimeClass",
        "SelfSubjectAccessReview" "SelfSubjectRulesReview",
        "StorageClass",
        "SubjectAccessReview",
        "TokenReview",
        "PersistentVolume" "ValidatingWebhookConfiguration",
        "VolumeAttachment",
    }


def owned_name_from_dict(obj: T.Mapping[str, T.Any], chart: str) -> str:
    prefix = obj["metadata"].get("namespace")
    if prefix is None or is_cluster_scoped(obj["kind"]):
        prefix = chart
    return prefix + "/" + obj["metadata"]["name"]


def owned_name(obj: ApiObject) -> str:
    prefix = obj.metadata.namespace
    if prefix is None or is_cluster_scoped(obj.kind):
        prefix = obj.chart.node.id
    return prefix + "/" + obj.name
