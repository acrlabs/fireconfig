from typing import Any
from typing import List
from typing import Mapping
from typing import MutableMapping
from typing import Optional
from typing import Tuple
from typing import Union

from cdk8s import ApiObject
from cdk8s import Chart
from cdk8s import JsonPatch

from fireconfig import k8s
from fireconfig.container import ContainerBuilder
from fireconfig.types import TaintEffect
from fireconfig.volume import VolumesBuilder


_APP_LABEL = "fireconfig.io/app"
_STANDARD_NAMESPACES = [
    'default',
    'kube-node-lease',
    'kube-public',
    'kube-system',
]


class DeploymentBuilder:
    def __init__(self, *, namespace: str, app_key: str):
        self._namespace = namespace
        self._annotations: MutableMapping[str, str] = {}
        self._labels: MutableMapping[str, str] = {}
        self._replicas: Union[int, Tuple[int, int]] = 1
        self._app_key = app_key
        self._selector = {_APP_LABEL: app_key}

        self._pod_annotations: MutableMapping[str, str] = {}
        self._pod_labels: MutableMapping[str, str] = dict(self._selector)
        self._containers: List[ContainerBuilder] = []
        self._node_selector: Optional[Mapping[str, str]] = None
        self._service_account_role: Optional[str] = None
        self._service_account_role_is_cluster_role: bool = False
        self._service: bool = False
        self._service_name: str = f"{self._app_key}-svc"
        self._service_ports: Optional[List[int]] = None
        self._service_object: Optional[k8s.KubeService] = None
        self._tolerations: List[Tuple[str, str, TaintEffect]] = []
        self._volumes: Optional[VolumesBuilder] = None
        self._deps: List[ApiObject] = []

    def get_service_address(self) -> str:
        return f'{self._service_name}.{self._namespace}'

    def with_annotation(self, key: str, value: str) -> 'DeploymentBuilder':
        self._annotations[key] = value
        return self

    def with_label(self, key: str, value: str) -> 'DeploymentBuilder':
        self._labels[key] = value
        return self

    def with_replicas(self, min_replicas: int, max_replicas: Optional[int] = None) -> 'DeploymentBuilder':
        if max_replicas is not None:
            if min_replicas > max_replicas:
                raise ValueError(f'min_replicas cannot be larger than max_replicas: {min_replicas} > {max_replicas}')
            self._replicas = (min_replicas, max_replicas)
        else:
            self._replicas = min_replicas
        return self

    def with_pod_annotation(self, key: str, value: str) -> 'DeploymentBuilder':
        self._pod_annotations[key] = value
        return self

    def with_pod_label(self, key: str, value: str) -> 'DeploymentBuilder':
        self._pod_labels[key] = value
        return self

    def with_containers(self, *containers: ContainerBuilder) -> 'DeploymentBuilder':
        self._containers.extend(containers)
        return self

    def with_node_selector(self, key: str, value: str) -> 'DeploymentBuilder':
        self._node_selector = {key: value}
        return self

    def with_service(self, ports: Optional[List[int]] = None) -> 'DeploymentBuilder':
        self._service = True
        self._service_ports = ports
        return self

    def with_service_account_and_role_binding(
        self,
        role_name: str,
        is_cluster_role: bool = False,
    ) -> 'DeploymentBuilder':
        self._service_account_role = role_name
        self._service_account_role_is_cluster_role = is_cluster_role
        return self

    def with_toleration(
        self,
        key: str,
        value: str = "",
        effect: TaintEffect = TaintEffect.NoExecute,
    ) -> 'DeploymentBuilder':
        self._tolerations.append((key, value, effect))
        return self

    def with_dependencies(self, *deps: ApiObject) -> 'DeploymentBuilder':
        self._deps.extend(deps)
        return self

    def build(self, chart: Chart) -> k8s.KubeDeployment:
        if self._namespace not in _STANDARD_NAMESPACES:
            ns = k8s.KubeNamespace(chart, "ns", metadata={"name": self._namespace})
            self._deps.insert(0, ns)

        meta: MutableMapping[str, Any] = {"namespace": self._namespace}
        if self._annotations:
            meta["annotations"] = self._annotations
        if self._labels:
            meta["labels"] = self._labels

        pod_meta: MutableMapping[str, Any] = {"namespace": self._namespace}
        if self._pod_annotations:
            pod_meta["annotations"] = self._pod_annotations
        pod_meta["labels"] = self._pod_labels

        if type(self._replicas) is tuple:
            replicas: Optional[int] = None
            raise NotImplementedError("No support for HPA currently")
        else:
            replicas = self._replicas  # type: ignore

        optional: MutableMapping[str, Any] = {}
        if self._node_selector is not None:
            optional["node_selector"] = self._node_selector

        if self._service_account_role is not None:
            sa = self._build_service_account(chart)
            rb = self._build_role_binding_for_service_account(
                chart, sa,
                self._service_account_role,
                self._service_account_role_is_cluster_role,
            )
            self._deps.append(sa)
            self._deps.append(rb)
            optional["service_account_name"] = sa.name

        if self._service:
            if self._service_ports is None:
                self._service_ports = []
                for c in self._containers:
                    self._service_ports.extend(c.get_ports())
            self._service_object = self._build_service(chart)
            self._deps.append(self._service_object)

        if len(self._tolerations) > 0:
            optional["tolerations"] = [
                {"key": t[0], "value": t[1], "effect": t[2]} for t in self._tolerations
            ]

        vols: Mapping[str, Mapping[str, Any]] = dict()
        for c in self._containers:
            vols = {**vols, **c.get_volumes()}

        if vols:
            optional["volumes"] = list(vols.values())

        depl = k8s.KubeDeployment(
            chart, "deployment",
            metadata=k8s.ObjectMeta(**meta),
            spec=k8s.DeploymentSpec(
                selector=k8s.LabelSelector(match_labels=self._selector),
                replicas=replicas,
                template=k8s.PodTemplateSpec(
                    metadata=k8s.ObjectMeta(**pod_meta),
                    spec=k8s.PodSpec(
                        containers=[c.build() for c in self._containers],
                        **optional,
                    ),
                )
            )
        )

        for i in range(len(self._containers)):
            depl.add_json_patch(JsonPatch.add(
                f"/spec/template/spec/containers/{i}/env/-",
                {"name": "POD_OWNER", "value": depl.name},
            ))

        for d in self._deps:
            depl.add_dependency(d)

        return depl

    def _build_service_account(self, chart: Chart) -> k8s.KubeServiceAccount:
        return k8s.KubeServiceAccount(
            chart, "service-account",
            metadata={"namespace": self._namespace},
        )

    def _build_service(self, chart: Chart) -> k8s.KubeService:
        assert self._service_ports
        return k8s.KubeService(
            chart, "service",
            metadata={"name": self._service_name, "namespace": self._namespace},
            spec=k8s.ServiceSpec(
                ports=[
                    k8s.ServicePort(port=p, target_port=k8s.IntOrString.from_number(p))
                    for p in self._service_ports
                ],
                selector=self._selector,
            ),
        )

    def _build_role_binding_for_service_account(
        self,
        chart: Chart,
        service_account: k8s.KubeServiceAccount,
        role_name: str,
        is_cluster_role: bool,
    ) -> Union[k8s.KubeClusterRoleBinding, k8s.KubeRoleBinding]:

        subjects = [k8s.Subject(
            kind="ServiceAccount",
            name=service_account.name,
            namespace=self._namespace,
        )]
        role_ref = k8s.RoleRef(
            api_group="rbac.authorization.k8s.io",
            kind="ClusterRole" if is_cluster_role else "Role",
            name=role_name,
        )

        if is_cluster_role:
            return k8s.KubeClusterRoleBinding(chart, "cluster-role-binding", subjects=subjects, role_ref=role_ref)
        else:
            return k8s.KubeRoleBinding(chart, "role-binding", subjects=subjects, role_ref=role_ref)
