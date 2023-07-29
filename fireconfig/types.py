from enum import StrEnum


class Capability(StrEnum):
    DEBUG = "SYS_PTRACE"


class DownwardAPIField(StrEnum):
    NAME = "metadata.name"
    NAMESPACE = "metadata.namespace"
    UID = "metadata.uid"
    ANNOTATION = "metadata.annotations[{}]"
    LABEL = "metadata.labels[{}]"


class TaintEffect(StrEnum):
    NoExecute = "NoExecute"
    NoSchedule = "NoSchedule"
    PreferNoSchedule = "PreferNoSchedule"
