import hashlib


def stable_identifier(namespace: str, natural_key: str) -> str:
    digest = hashlib.sha256(f"{namespace}:{natural_key}".encode()).hexdigest()[:32]
    return f"{namespace}_{digest}"
