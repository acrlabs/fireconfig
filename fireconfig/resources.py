import typing as T

from fireconfig import k8s

ResourceMap = T.Mapping[str, T.Union[int, str]]
QuantityMap = T.Mapping[str, k8s.Quantity]
MutableQuantityMap = T.MutableMapping[str, k8s.Quantity]


def parse_resource_map(m: ResourceMap) -> QuantityMap:
    q: MutableQuantityMap = {}
    for k, v in m.items():
        match v:
            case str():
                q[k] = k8s.Quantity.from_string(v)
            case int():
                q[k] = k8s.Quantity.from_number(v)
    return q


class Resources:
    def __init__(self, requests: T.Optional[ResourceMap], limits: T.Optional[ResourceMap]):
        self.requests: T.Optional[QuantityMap] = None
        self.limits: T.Optional[QuantityMap] = None

        if requests is not None:
            self.requests = parse_resource_map(requests)
        if limits is not None:
            self.limits = parse_resource_map(limits)
