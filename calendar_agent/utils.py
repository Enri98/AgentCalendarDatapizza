import os


def env_truthy(name: str, default: str = "0") -> bool:
    value = os.getenv(name, default)
    return value.strip().lower() in {"1", "true", "yes"}
