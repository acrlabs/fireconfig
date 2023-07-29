from typing import Mapping
from typing import Optional
from typing import Sequence

from fireconfig import k8s


class VolumesBuilder:
    def __init__(self):
        self._volumes = {}
        self._volume_mounts = {}

    def with_config_map(self, name: str, mount_path: str, config_map: k8s.KubeConfigMap) -> 'VolumesBuilder':
        self._volumes[name] = ("configMap", {
            "name": config_map.name,
            "items": [{
                "key": cm_entry,
                "path": cm_entry,
            } for cm_entry in config_map.to_json()["data"]],
            })

        self._volume_mounts[name] = mount_path
        return self

    def get_path_to(self, name: str) -> str:
        path = self._volume_mounts[name] + '/'
        match self._volumes[name]:
            case ("configMap", data):
                path += data["items"][0]["path"]
        return path

    def build_mounts(self, names: Optional[Sequence[str]] = None) -> Sequence[Mapping]:
        if names is None:
            names = self._volume_mounts.keys()

        return [{"name": name, "mountPath": self._volume_mounts[name]} for name in names]

    def build_volumes(self) -> Sequence[Mapping]:
        return [{"name": name, volume_type: data} for name, (volume_type, data) in self._volumes.items()]
