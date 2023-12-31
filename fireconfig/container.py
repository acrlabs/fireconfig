from typing import Any
from typing import Dict
from typing import Mapping
from typing import Optional
from typing import Sequence
from typing import Set

from fireconfig import k8s
from fireconfig.env import EnvBuilder
from fireconfig.resources import Resources
from fireconfig.types import Capability
from fireconfig.volume import VolumesBuilder


class ContainerBuilder:
    def __init__(self, name: str, image: str, command: Optional[str] = None, args: Optional[Sequence[str]] = None):
        self._name = name
        self._image = image

        self._args = args
        self._command = command
        self._env: Optional[EnvBuilder] = None
        self._env_names: Optional[Sequence[str]] = None
        self._resources: Optional[Resources] = None
        self._ports: Sequence[int] = []
        self._volumes: Optional[VolumesBuilder] = None
        self._volume_names: Optional[Sequence[str]] = None
        self._capabilities: Set[Capability] = set()

    def get_ports(self) -> Sequence[int]:
        return self._ports

    def get_volumes(self) -> Mapping[str, Mapping[str, Any]]:
        if self._volumes is None:
            return dict()

        return self._volumes.build_volumes(self._volume_names)

    def with_env(self, env: EnvBuilder, names: Optional[Sequence[str]] = None) -> 'ContainerBuilder':
        self._env = env
        self._env_names = names
        return self

    def with_resources(
        self, *,
        requests: Optional[Mapping[str, Any]] = None,
        limits: Optional[Mapping[str, Any]] = None,
    ) -> 'ContainerBuilder':
        self._resources = Resources(requests, limits)
        return self

    def with_ports(self, *ports: int) -> 'ContainerBuilder':
        self._ports = ports
        return self

    def with_security_context(self, capability: Capability) -> 'ContainerBuilder':
        self._capabilities.add(capability)
        return self

    def with_volumes(self, volumes: VolumesBuilder, names: Optional[Sequence[str]] = None) -> 'ContainerBuilder':
        self._volumes = volumes
        self._volume_names = names
        return self

    def build(self) -> k8s.Container:
        optional: Dict[str, Any] = {}
        if self._command:
            optional["command"] = [self._command]
        if self._args:
            optional["args"] = self._args

        if self._env:
            optional["env"] = self._env.build(self._env_names)
        else:
            optional["env"] = []
        if self._ports:
            optional["ports"] = [
                k8s.ContainerPort(container_port=p) for p in self._ports
            ]
        if self._resources is not None:
            optional["resources"] = {}
            if self._resources.limits is not None:
                optional["resources"]["limits"] = self._resources.limits
            if self._resources.requests is not None:
                optional["resources"]["requests"] = self._resources.requests
        if self._volumes:
            optional["volume_mounts"] = self._volumes.build_mounts(self._volume_names)
        if self._capabilities:
            optional["security_context"] = {"capabilities": {"add": [c for c in self._capabilities]}}

        return k8s.Container(
            name=self._name,
            image=self._image,
            **optional,
        )
