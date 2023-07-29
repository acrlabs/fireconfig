from typing import Mapping
from typing import Optional
from typing import Sequence

from fireconfig.types import DownwardAPIField


class EnvBuilder:
    def __init__(self):
        self._env = {}

    def with_field_ref(self, name: str, field: DownwardAPIField, key: Optional[str] = None) -> 'EnvBuilder':
        field_str = str(field)
        if field in (DownwardAPIField.ANNOTATION, DownwardAPIField.LABEL):
            field_str = field_str.format(key)

        self._env[name] = ("valueFrom", {"fieldRef": {"fieldPath": field_str}})
        return self

    def build(self, names: Optional[Sequence[str]] = None) -> Sequence[Mapping]:
        if names is None:
            names = self._env.keys()

        return [{"name": name, self._env[name][0]: self._env[name][1]} for name in names]
