from typing import Any


class MissingType:
    def __str__(self) -> str:
        return "Missing"

    def __repr__(self) -> str:
        return "MISSING"


MISSING: Any = MissingType()
