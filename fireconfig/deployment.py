import typing as T

from cdk8s import Chart
from cdk8s import JsonPatch

from fireconfig import k8s
from fireconfig.container import ContainerBuilder
from fireconfig.object import ObjectBuilder
from fireconfig.types import TaintEffect
from fireconfig.volume import VolumeDefsWithObject
from fireconfig.volume import VolumesBuilder

_APP_LABEL_KEY = "fireconfig.io/app"


class DeploymentBuilder(ObjectBuilder):
    def __init__(self, *, app_label: str, tag: T.Optional[str] = None):
        self._selector = {_APP_LABEL_KEY: app_label}
        super().__init__(labels=self._selector)

        self._replicas: T.Union[int, T.Tuple[int, int]] = 1
        self._app_label = app_label
        self._tag = "" if tag is None else f"{tag}-"

        self._pod_annotations: T.MutableMapping[str, str] = {}
        self._pod_labels: T.MutableMapping[str, str] = dict(self._selector)
        self._containers: T.List[ContainerBuilder] = []
        self._node_selector: T.Optional[T.Mapping[str, str]] = None
        self._service_account_role: T.Optional[str] = None
        self._service_account_role_is_cluster_role: bool = False
        self._service: bool = False
        self._service_name: str = f"{self._app_label}-svc"
        self._service_ports: T.Optional[T.List[int]] = None
        self._tolerations: T.List[T.Tuple[str, str, TaintEffect]] = []
        self._volumes: T.Optional[VolumesBuilder] = None

    @property
    def service_name(self) -> str:
        return self._service_name

    def with_replicas(self, min_replicas: int, max_replicas: T.Optional[int] = None) -> T.Self:
        if max_replicas is not None:
            if min_replicas > max_replicas:
                raise ValueError(f'min_replicas cannot be larger than max_replicas: {min_replicas} > {max_replicas}')
            self._replicas = (min_replicas, max_replicas)
        else:
            self._replicas = min_replicas
        return self

    def with_pod_annotation(self, key: str, value: str) -> T.Self:
        self._pod_annotations[key] = value
        return self

    def with_pod_label(self, key: str, value: str) -> T.Self:
        self._pod_labels[key] = value
        return self

    def with_containers(self, *containers: ContainerBuilder) -> T.Self:
        self._containers.extend(containers)
        return self

    def with_node_selector(self, key: str, value: str) -> T.Self:
        self._node_selector = {key: value}
        return self

    def with_service(self, ports: T.Optional[T.List[int]] = None) -> T.Self:
        self._service = True
        self._service_ports = ports
        return self

    def with_service_account_and_role_binding(self, role_name: str, is_cluster_role: bool = False) -> T.Self:
        self._service_account_role = role_name
        self._service_account_role_is_cluster_role = is_cluster_role
        return self

    def with_toleration(self, key: str, value: str = "", effect: TaintEffect = TaintEffect.NoExecute) -> T.Self:
        self._tolerations.append((key, value, effect))
        return self

    def _build(self, meta: k8s.ObjectMeta, chart: Chart) -> k8s.KubeDeployment:
        pod_meta: T.MutableMapping[str, T.Any] = {}
        if self._pod_annotations:
            pod_meta["annotations"] = self._pod_annotations
        pod_meta["labels"] = self._pod_labels

        if type(self._replicas) is tuple:
            replicas: T.Optional[int] = None
            raise NotImplementedError("No support for HPA currently")
        else:
            replicas = self._replicas  # type: ignore

        optional: T.MutableMapping[str, T.Any] = {}
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
                    self._service_ports.extend(c.ports)
            self._build_service(chart)

        if len(self._tolerations) > 0:
            optional["tolerations"] = [
                {"key": t[0], "value": t[1], "effect": t[2]} for t in self._tolerations
            ]

        vols: VolumeDefsWithObject = dict()
        for c in self._containers:
            vols = {**vols, **c.build_volumes(chart)}

        if vols:
            optional["volumes"] = []
            for (defn, obj) in vols.values():
                optional["volumes"].append(defn)
                if obj is not None:
                    self._deps.append(obj)

        depl = k8s.KubeDeployment(
            chart, f"{self._tag}depl",
            metadata=meta,
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

        return depl

    # TODO maybe move these into separate files at some point?
    def _build_service_account(self, chart: Chart) -> k8s.KubeServiceAccount:
        return k8s.KubeServiceAccount(chart, f"{self._tag}sa")

    def _build_service(self, chart: Chart) -> k8s.KubeService:
        assert self._service_ports
        return k8s.KubeService(
            chart, "service",
            metadata={"name": self._service_name},
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
    ) -> T.Union[k8s.KubeClusterRoleBinding, k8s.KubeRoleBinding]:

        subjects = [k8s.Subject(
            kind="ServiceAccount",
            name=service_account.name,
            namespace=chart.namespace,
        )]
        role_ref = k8s.RoleRef(
            api_group="rbac.authorization.k8s.io",
            kind="ClusterRole" if is_cluster_role else "Role",
            name=role_name,
        )

        if is_cluster_role:
            return k8s.KubeClusterRoleBinding(chart, f"{self._tag}crb", subjects=subjects, role_ref=role_ref)
        else:
            return k8s.KubeRoleBinding(chart, f"{self._tag}rb", subjects=subjects, role_ref=role_ref)
