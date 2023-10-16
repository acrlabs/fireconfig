from enum import StrEnum


class Capability(StrEnum):
    DEBUG = "SYS_PTRACE"


class DownwardAPIField(StrEnum):
    NAME = "metadata.name"
    NAMESPACE = "metadata.namespace"
    UID = "metadata.uid"
    ANNOTATION = "metadata.annotations[{}]"
    LABEL = "metadata.labels[{}]"
    SERVICE_ACCOUNT_NAME = "spec.serviceAccountName"
    NODE_NAME = "spec.nodeName"
    HOST_IP = "status.hostIP"
    HOST_IPS = "status.hostIPs"
    POD_IP = "status.podIP"
    POD_IPS = "status.podIPs"


class TaintEffect(StrEnum):
    NoExecute = "NoExecute"
    NoSchedule = "NoSchedule"
    PreferNoSchedule = "PreferNoSchedule"
