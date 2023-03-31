import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .dict_config import DictConfig


class ConfigueDumper:
    @classmethod
    def from_pyyaml(cls, serialized_config: str) -> str:
        serialized_config = re.sub(
            r"^(\s*?)(\w+):( &id\d{3})? !!python/name:(.*?) ''$",
            r"\g<1>\g<2>:\g<3> !ext \g<4>",
            serialized_config,
            flags=re.MULTILINE,
        )
        return serialized_config.strip(" \n") + "\n"

    @classmethod
    def from_config(cls, config: "DictConfig") -> str:
        return cls.from_pyyaml(config.to_configue())
