from __future__ import annotations

import functools
from collections.abc import Mapping
from enum import IntEnum
from functools import reduce
from typing import Any, Dict, MutableMapping, Optional, Sequence, Type

import yaml

from .dumper import ConfigueDumper
from .loader import load_from_string
from .traversers import DataclassInstance, Traverser


class ListMergeMode(IntEnum):
    EXTEND = 0
    REPLACE = 1


def _deepmerge(destination: DictConfig, source: Mapping, mode: ListMergeMode) -> DictConfig:
    for key in source:
        if key in destination:
            if isinstance(destination[key], MutableMapping) and isinstance(source[key], Mapping):
                _deepmerge(destination[key], source[key], mode)
            elif isinstance(destination[key], list) and isinstance(source[key], list) and mode == ListMergeMode.EXTEND:
                destination[key].extend(source[key])
            elif destination[key] is source[key]:
                pass
            else:
                destination[key] = source[key]
        else:
            destination[key] = source[key]
    return destination


class DictConfig(dict[str, Any]):
    def __init__(self, *args: Dict[str, Any], **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        for key, value in self.items():
            if isinstance(value, dict):
                self[key] = self.__class__(value)

    def to_configue(self) -> str:
        return ConfigueDumper.from_pyyaml(yaml.dump(self, Dumper=yaml.Dumper, sort_keys=False))

    @classmethod
    def from_type(cls, type_: Type[DataclassInstance], initial_config: Optional[Dict[str, Any]] = None) -> DictConfig:
        config, _ = Traverser.traverse_type(type_, initial_config)
        return cls(**config)

    @classmethod
    def from_dotlist(cls, dotlist: Sequence[str]) -> DictConfig:
        config = cls()
        for arg in dotlist:
            idx = arg.find("=")
            if idx == -1:
                key = arg
                value = None
            else:
                key = arg[0:idx]
                value = arg[idx + 1 :]
                value = load_from_string(value.strip("\"'"), instantiate=False)

            subkeys = key.split(".")
            sub_config = config
            for subkey in subkeys[:-1]:
                if subkey not in sub_config:
                    sub_config[subkey] = cls()
                sub_config = sub_config[subkey]
            sub_config[subkeys[-1]] = value
        return config

    def merge(self, *configs: DictConfig, mode: ListMergeMode = ListMergeMode.EXTEND) -> None:
        reduce(functools.partial(_deepmerge, mode=mode), configs, self)


yaml.add_representer(DictConfig, lambda dumper, data: dumper.represent_mapping("tag:yaml.org,2002:map", data.items()))
