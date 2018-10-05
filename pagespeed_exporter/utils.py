import re

_CTS_RE1 = re.compile(r'(.)([A-Z][a-z]+)')
_CTS_RE2 = re.compile(r'([a-z0-9])([A-Z])')


def camel_to_snake(name: str) -> str:
    name = _CTS_RE1.sub(r'\1_\2', name)
    return _CTS_RE2.sub(r'\1_\2', name).lower()
