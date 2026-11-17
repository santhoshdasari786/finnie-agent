# core/registry.py
from collections import defaultdict


_REGISTRY: dict[str, dict[str, type]] = defaultdict(dict)

def     register(kind: str, name: str):
    def deco(cls):
        if name in _REGISTRY[kind]:
            raise ValueError(f"{kind} '{name}' already registered by {_REGISTRY[kind][name].__name__}")
        _REGISTRY[kind][name] = cls
        return cls
    return deco