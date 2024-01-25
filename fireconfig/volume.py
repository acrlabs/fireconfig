from typing import Any
from typing import Iterable
from typing import Mapping
from typing import MutableMapping
from typing import Optional
from typing import Self
from typing import Sequence
from typing import Tuple

from cdk8s import ApiObject
from cdk8s import Chart

from fireconfig import k8s

VolumeDefsWithObject = Mapping[str, Tuple[Mapping[str, Any], Optional[ApiObject]]]


class VolumesBuilder:
    def __init__(self) -> None:
        self._volume_mounts: MutableMapping[str, str] = {}
        self._config_map_data: MutableMapping[str, Mapping[str, str]] = {}

    def with_config_map(self, vol_name: str, mount_path: str, data: Mapping[str, str]) -> Self:
        self._config_map_data[vol_name] = data
        self._volume_mounts[vol_name] = mount_path
        return self

    def get_path_to_config_map(self, vol_name: str, path_name: str) -> str:
        assert vol_name in self._config_map_data and path_name in self._config_map_data[vol_name]
        path = self._volume_mounts[vol_name] + '/' + path_name
        return path

    def build_mounts(self, names: Optional[Iterable[str]] = None) -> Sequence[Mapping]:
        if names is None:
            names = self._volume_mounts.keys()

        return [{"name": name, "mountPath": self._volume_mounts[name]} for name in names]

    def build_volumes(self, chart: Chart, names: Optional[Iterable[str]] = None) -> VolumeDefsWithObject:
        if names is None:
            names = self._volume_mounts.keys()

        volumes = {}
        for vol_name, data in self._config_map_data.items():
            if vol_name not in names:
                continue

            cm = k8s.KubeConfigMap(chart, vol_name, data=data)
            volumes[vol_name] = ({
                "name": vol_name,
                "configMap": {
                    "name": cm.name,
                    "items": [{
                        "key": cm_entry,
                        "path": cm_entry,
                    } for cm_entry in data],
                }
            }, cm)

        return volumes
