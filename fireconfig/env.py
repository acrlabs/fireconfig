from typing import KeysView
from typing import Mapping
from typing import MutableMapping
from typing import Optional
from typing import Self
from typing import Sequence
from typing import Tuple
from typing import Union

from fireconfig.types import DownwardAPIField


class EnvBuilder:
    def __init__(self, env: Mapping[str, str] = dict()):
        self._env: MutableMapping[str, Tuple[str, Union[str, Mapping]]] = {k: ("value", v) for (k, v) in env.items()}

    def with_field_ref(self, name: str, field: DownwardAPIField, key: Optional[str] = None) -> Self:
        field_str = str(field)
        if field in (DownwardAPIField.ANNOTATION, DownwardAPIField.LABEL):
            field_str = field_str.format(key)

        self._env[name] = ("valueFrom", {"fieldRef": {"fieldPath": field_str}})
        return self

    def build(self, names: Optional[Union[Sequence[str], KeysView[str]]] = None) -> Sequence[Mapping]:
        if names is None:
            names = self._env.keys()

        return [{"name": name, self._env[name][0]: self._env[name][1]} for name in names]
