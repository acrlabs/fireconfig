import typing as T

from fireconfig.types import DownwardAPIField


class EnvBuilder:
    def __init__(self, env: T.Mapping[str, str] = dict()):
        self._env: T.MutableMapping[str, T.Tuple[str, T.Union[str, T.Mapping]]] = {
            k: ("value", v) for (k, v) in env.items()
        }
        self._env_from: T.List[T.Mapping] = []

    def with_field_ref(self, name: str, field: DownwardAPIField, key: T.Optional[str] = None) -> T.Self:
        field_str = str(field)
        if field in {DownwardAPIField.ANNOTATION, DownwardAPIField.LABEL}:
            field_str = field_str.format(key)

        self._env[name] = ("valueFrom", {"fieldRef": {"fieldPath": field_str}})
        return self

    def with_secrets_from(self, secret_name: str) -> T.Self:
        self._env_from.append({"secretRef": {"name": secret_name}})
        return self

    def with_secret(self, name: str, secret_name: str, secret_key_name: str) -> T.Self:
        self._env[name] = ("valueFrom", {"secretKeyRef": {"name": secret_name, "key": secret_key_name}})
        return self

    def build(self, names: T.Optional[T.Union[T.Sequence[str], T.KeysView[str]]] = None) -> T.Sequence[T.Mapping]:
        if names is None:
            names = self._env.keys()

        return [{"name": name, self._env[name][0]: self._env[name][1]} for name in names]

    def build_from(self) -> T.Sequence[T.Mapping]:
        return self._env_from
