from src.rag.common.registry import _REGISTRY 

# def build(kind: str, spec: dict):
#     cls = _REGISTRY[kind][spec["type"]]
#     return cls(**spec.get("params", {}))

def build(kind: str, spec: dict, **extra):
    name = spec["type"]

    if name not in _REGISTRY.get(kind, {}):
        if kind not in _REGISTRY:
            raise ValueError(f"Unknown kind '{kind}'. Known kinds: {sorted(_REGISTRY)}")
        raise ValueError(f"Unknown {kind} '{name}'. Available: {sorted(_REGISTRY[kind])}")


    try:
        cls = _REGISTRY[kind][name]
    except KeyError:
        raise ValueError(f"Unknown {kind} '{name}'. Available: {sorted(_REGISTRY[kind])}") from None
    kwargs = {k: v for k, v in spec.items() if k != "type"}
    return cls(**kwargs, **extra)       # extra = runtime deps, e.g. model_id for the store
