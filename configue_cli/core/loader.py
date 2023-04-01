import os
import tempfile
from typing import TYPE_CHECKING, Any, List, Type, Union, cast

from configue.configue_loader import ConfigueLoader
from configue.file_loader import FileLoader
from configue.root_loader import RootLoader
from yaml import FullLoader, Loader, MappingNode
from yaml.constructor import UnsafeConstructor

if TYPE_CHECKING:
    from .dict_config import DictConfig


class NonInstanciatingConfigueLoader(ConfigueLoader):
    def construct_yaml_map(self, node: MappingNode) -> MappingNode:
        return cast(MappingNode, super(FullLoader, self).construct_yaml_map(node))  # type: ignore[misc]


class NonInstanciatingFileLoader(FileLoader):
    def __init__(self, file_path: str, root_loader: RootLoader) -> None:
        super().__init__(file_path, root_loader)

        loader_cls: Type[Loader] = cast(
            Type[Loader],
            type("CustomLoader", (NonInstanciatingConfigueLoader,), {"yaml_loader": self}),
        )

        loader_cls.add_multi_constructor("!import", self._load_import)
        loader_cls.add_constructor("!path", self._load_path)
        loader_cls.add_constructor("!cfg", self._load_cfg)
        loader_cls.add_constructor("!ext", self._load_ext)
        loader_cls.add_constructor("tag:yaml.org,2002:map", loader_cls.construct_yaml_map)
        loader_cls.add_multi_constructor("tag:yaml.org,2002:python/object:", UnsafeConstructor.construct_python_object)
        loader_cls.add_multi_constructor(
            "tag:yaml.org,2002:python/object/new:", UnsafeConstructor.construct_python_object_new
        )

        with open(self._file_path, encoding="utf-8") as config_file:
            self._loader = loader_cls(config_file)
            self._root_node = self._loader.get_single_node()
        self._loader.dispose()


class InstanciatingFileLoader(FileLoader):
    def __init__(self, file_path: str, root_loader: RootLoader) -> None:
        super().__init__(file_path, root_loader)

        loader_cls: Type[Loader] = cast(
            Type[Loader],
            type("CustomLoader", (ConfigueLoader,), {"yaml_loader": self}),
        )

        loader_cls.add_multi_constructor("!import", self._load_import)
        loader_cls.add_constructor("!path", self._load_path)
        loader_cls.add_constructor("!cfg", self._load_cfg)
        loader_cls.add_constructor("!ext", self._load_ext)
        loader_cls.add_constructor("tag:yaml.org,2002:map", loader_cls.construct_yaml_map)
        loader_cls.add_multi_constructor("tag:yaml.org,2002:python/object:", UnsafeConstructor.construct_python_object)
        loader_cls.add_multi_constructor(
            "tag:yaml.org,2002:python/object/new:", UnsafeConstructor.construct_python_object_new
        )

        with open(self._file_path, encoding="utf-8") as config_file:
            self._loader = loader_cls(config_file)
            self._root_node = self._loader.get_single_node()
        self._loader.dispose()


class NonInstanciatingRootLoader(RootLoader):
    def load_file(self, file_path: str, sub_path: Union[str, List[str]]) -> Any:
        if file_path not in self._file_loaders_by_file:
            self._file_loaders_by_file[file_path] = NonInstanciatingFileLoader(file_path, self)
        return self._file_loaders_by_file[file_path].load(sub_path)


class InstanciatingRootLoader(RootLoader):
    def load_file(self, file_path: str, sub_path: Union[str, List[str]]) -> Any:
        if file_path not in self._file_loaders_by_file:
            self._file_loaders_by_file[file_path] = InstanciatingFileLoader(file_path, self)
        return self._file_loaders_by_file[file_path].load(sub_path)


def load_from_path(
    file_path: str,
    *,
    sub_path: Union[str, List[str]] = "",
    instantiate: bool = True,
) -> Any:
    if instantiate:
        return InstanciatingRootLoader(file_path).load_root_file(sub_path, None)
    return NonInstanciatingRootLoader(file_path).load_root_file(sub_path, None)


def load_from_string(serialized_config: str, *, instantiate: bool = True) -> Any:
    with tempfile.TemporaryDirectory() as temp_dir:
        with open(os.path.join(temp_dir, "config.yml"), "w", encoding="utf-8") as writer:
            writer.write(serialized_config)
        config = load_from_path(os.path.join(temp_dir, "config.yml"), instantiate=instantiate)
    return config


def load_from_config(config: "DictConfig", *, instantiate: bool = True) -> Any:
    return load_from_string(config.to_configue(), instantiate=instantiate)
