from typing import Mapping
from typing import MutableMapping
from typing import Optional
from typing import Union

from fireconfig import k8s

ResourceMap = Mapping[str, Union[int, str]]
QuantityMap = Mapping[str, k8s.Quantity]
MutableQuantityMap = MutableMapping[str, k8s.Quantity]


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
    def __init__(self, requests: Optional[ResourceMap], limits: Optional[ResourceMap]) -> None:
        self.requests: Optional[QuantityMap] = None
        self.limits: Optional[QuantityMap] = None

        if requests is not None:
            self.requests = parse_resource_map(requests)
        if limits is not None:
            self.limits = parse_resource_map(limits)
